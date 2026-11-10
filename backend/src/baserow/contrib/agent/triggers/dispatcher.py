from collections.abc import Callable, Iterable

from django.contrib.auth.models import AbstractUser
from django.db import transaction

from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger

from baserow.core.feature_flags import FF_AGENT_BUILDER, feature_flag_is_enabled
from baserow.core.services.models import Service
from baserow.core.utils import exception_capturer

from ..constants import AgentReadinessState
from ..handler import AgentHandler
from ..models import AgentTrigger
from ..signals import agent_conversation_activity
from .data_providers import resolve_trigger_message


class AgentTriggerDispatcher:
    """Starts a shared conversation for every agent trigger an event applies to."""

    def on_event(
        self,
        services: Iterable[Service],
        event_payload: dict | Callable | None = None,
        user: AbstractUser | None = None,
        isolate_failures: bool = False,
    ) -> list:
        """
        Start one conversation per runnable trigger of the given services. Every
        matched trigger gets its payload first, so a schedule keeps advancing while
        its trigger is disabled or its agent can't run. A trigger that fails to
        start is logged and skipped whatever ``isolate_failures`` says: an agent
        bug must never fail the event's other listeners.

        :param services: The services the event applies to.
        :param event_payload: The payload, or a callable returning it per service.
        :param user: The user who caused the event, never stored.
        :param isolate_failures: Ignored, failures are always isolated.
        :return: An empty list, so listeners that return histories stay first.
        """

        try:
            with transaction.atomic():
                triggers, payloads = self._match(services, event_payload)
        except SoftTimeLimitExceeded:
            raise
        except Exception as e:
            logger.exception("Could not match agent triggers.")
            exception_capturer(e)
            return []
        if not feature_flag_is_enabled(FF_AGENT_BUILDER):
            logger.debug("Agent triggers skipped: the agent builder is off.")
            return []
        for trigger in triggers:
            self._start(trigger, payloads[trigger.id] or {})
        return []

    def _match(
        self, services: Iterable[Service], event_payload: dict | Callable | None
    ) -> tuple[list[AgentTrigger], dict[int, dict | None]]:
        """
        Find the triggers of the given services and resolve the payload of each.

        :param services: The services the event applies to.
        :param event_payload: The payload, or a callable returning it per service.
        :return: The matched triggers, and their payloads by trigger id.
        """

        services_by_id = {service.id: service for service in services}
        triggers = list(
            AgentTrigger.objects.filter(
                service_id__in=list(services_by_id)
            ).select_related("agent__workspace", "service")
        )
        # The callable gets the instances it handed over, which it then saves.
        payloads = {
            trigger.id: (
                event_payload(services_by_id[trigger.service_id])
                if callable(event_payload)
                else event_payload
            )
            for trigger in triggers
        }
        return triggers, payloads

    def _is_runnable(self, trigger: AgentTrigger) -> bool:
        """
        Whether the trigger may start a conversation now, logging why not.

        :param trigger: The matched trigger, with its agent and workspace.
        :return: True when the trigger is enabled and its agent can reply.
        """

        agent = trigger.agent
        workspace = agent.workspace
        if not trigger.enabled:
            reason = "it is disabled"
        elif agent.trashed or workspace is None or workspace.trashed:
            reason = "its agent is trashed or is a snapshot"
        elif (
            AgentHandler().get_configuration_readiness(agent)[0]
            != AgentReadinessState.READY
        ):
            reason = "its agent isn't ready"
        else:
            return True
        logger.debug("Agent trigger {} skipped: {}.", trigger.id, reason)
        return False

    def _start(self, trigger: AgentTrigger, payload: dict) -> None:
        """
        Start the trigger's conversation in a savepoint if it is runnable, telling
        the readers. A failure rolls back only this trigger and is logged.

        :param trigger: The trigger that fired, with its agent.
        :param payload: The event payload the message formula reads.
        """

        try:
            with transaction.atomic():
                if not self._is_runnable(trigger):
                    return
                content = resolve_trigger_message(trigger, payload)
                handler = AgentHandler()
                conversation = handler.start_trigger_conversation(trigger, content)
                run_id = next(
                    iter(handler.get_active_reply_runs(conversation).values()), None
                )
                agent_conversation_activity.send(
                    self, conversation=conversation, user=None, run_id=run_id
                )
        except SoftTimeLimitExceeded:
            # The task is out of time and must stop instead of starting the rest.
            raise
        except Exception as e:
            logger.exception("Could not start agent trigger {}.", trigger.id)
            exception_capturer(e)


agent_trigger_dispatcher = AgentTriggerDispatcher()
