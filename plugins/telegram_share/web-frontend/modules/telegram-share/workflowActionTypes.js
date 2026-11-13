import { OpenUrlWorkflowActionType } from '@baserow/modules/database/workflowActionTypes'
import { copyToClipboard } from '@baserow/modules/core/utils/clipboard'
import TelegramSendWorkflowActionForm from './components/TelegramSendWorkflowActionForm.vue'

// Telegram usernames are letters, digits and underscores, starting with a
// letter (core.telegram.org/api/links, "Public username links").
const USERNAME = /^[A-Za-z][A-Za-z0-9_]{3,31}$/

/**
 * The username in a cell, typed as "@name", "name" or a t.me link. Empty when
 * it isn't one. Phone numbers are refused: only usernames are linked.
 */
export function telegramUsername(value) {
  const name = `${value ?? ''}`
    .trim()
    .replace(/^(https?:\/\/)?(www\.)?(t|telegram)\.me\//i, '')
    .replace(/^@/, '')
    .split(/[/?#]/)[0]
  return USERNAME.test(name) ? name : ''
}

/**
 * Opens `t.me/<username>?text=<message>` in a new tab, so the clicker's own
 * Telegram opens the chat with the message typed in. Telegram only types it in
 * "if the user can write in the chat" (core.telegram.org/api/links), so an
 * empty box means the contact's privacy settings block the clicker; the toast
 * says so, and the message is copied to send another way.
 *
 * Extends the open URL action: the backend model is a subclass of it, so the
 * button opens the new tab on click (buttonField.js `openNewTab`).
 */
export class TelegramSendWorkflowActionType extends OpenUrlWorkflowActionType {
  static getType() {
    return 'telegram_send'
  }

  getOrder() {
    return 6
  }

  get form() {
    return TelegramSendWorkflowActionForm
  }

  get label() {
    return this.app.$i18n.t('telegramShare.label')
  }

  get icon() {
    return 'iconoir-send'
  }

  getErrorMessage(workflowAction, applicationContext) {
    if (!workflowAction.recipient?.formula) {
      return this.app.$i18n.t('telegramShare.noRecipient')
    }
    // The open URL checks without its "no URL" one: this action has no URL.
    return super.getErrorMessage(
      { ...workflowAction, url: { formula: 'telegram' } },
      applicationContext
    )
  }

  /**
   * The public link of the action's form, with the row's values filled in
   * when `prefill` is on (`prefill_field_<id>`, database/utils/form.js).
   */
  formLink(workflowAction, { row, fields }) {
    const form = workflowAction.form
    if (!form?.slug) {
      return ''
    }
    const url = new URL(
      this.app.$config.public.baserowEmbeddedShareUrl +
        this.app.$router.resolve({
          name: 'database-table-form',
          params: { slug: form.slug },
        }).href
    )
    if (workflowAction.prefill && row && fields) {
      for (const id of form.field_ids || []) {
        const field = fields.find((f) => f.id === id)
        const value = row[`field_${id}`]
        const fieldType = field && this.app.$registry.get('field', field.type)
        // A type the form can't prefill would only make the link longer.
        if (
          !fieldType?.canParseQueryParameter() ||
          value === null ||
          value === undefined
        ) {
          continue
        }
        const text = this.prefillText(fieldType, field, value)
        if (text) {
          url.searchParams.set(`prefill_field_${id}`, text)
        }
      }
    }
    return url.toString()
  }

  /**
   * A cell's value as the form's `parseQueryParameter` reads it back
   * (database/fieldTypes.js): CSV for links, which it looks up one by one, and
   * a bare comma between select options, which it splits on.
   */
  prefillText(fieldType, field, value) {
    if (field.type === 'link_row') {
      return Array.isArray(value) && value.length
        ? this.app.$papa.arrayToString(value.map((link) => link.value))
        : ''
    }
    if (field.type === 'multiple_select') {
      return fieldType.toHumanReadableString(field, value, ',')
    }
    return fieldType.toHumanReadableString(field, value)
  }

  async execute({ workflowAction, applicationContext }) {
    let username
    let text
    try {
      username = telegramUsername(
        this.resolveText(workflowAction.recipient, applicationContext)
      )
      text = [
        this.resolveText(workflowAction.message, applicationContext),
        this.formLink(workflowAction, applicationContext),
      ]
        .filter(Boolean)
        .join('\n\n')
    } catch {
      // Nothing here may throw: this runs from a click handler.
      username = ''
    }

    if (!username) {
      await this.app.$store.dispatch('toast/error', {
        title: this.app.$i18n.t('telegramShare.noUsernameTitle'),
        message: this.app.$i18n.t('telegramShare.noUsernameMessage'),
      })
      return false
    }

    const url = text
      ? `https://t.me/${username}?text=${encodeURIComponent(text)}`
      : `https://t.me/${username}`
    // Same as the open URL action's new tab: the tab the button opened on
    // click, or a new one.
    const tab = applicationContext.newTab?.take()
    if (tab) {
      const link = tab.document.createElement('a')
      link.href = url
      link.rel = 'noreferrer'
      tab.document.body.appendChild(link)
      link.click()
    } else {
      window.open(url, '_blank', 'noopener,noreferrer')
    }

    let copied = false
    if (text) {
      try {
        await copyToClipboard(text)
        copied = true
      } catch {
        // The new tab has focus, which some browsers refuse a copy for.
      }
    }
    await this.app.$store.dispatch('toast/info', {
      title: this.app.$i18n.t('telegramShare.openedTitle', { username }),
      message: this.app.$i18n.t(
        copied
          ? 'telegramShare.openedCopiedMessage'
          : 'telegramShare.openedMessage',
        { username }
      ),
    })
    return true
  }
}
