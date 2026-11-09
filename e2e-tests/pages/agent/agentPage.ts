import { Locator, Response, expect } from "@playwright/test";
import { BaserowPage, PageConfig } from "../baserowPage";
import { Agent } from "../../fixtures/agent/agent";

export class AgentPage extends BaserowPage {
  readonly agent: Agent;
  readonly configuration: Locator;

  constructor(pageConfig: PageConfig, agent: Agent) {
    super(pageConfig);
    this.agent = agent;
    this.configuration = this.page.locator(".agent-configuration");
  }

  getFullUrl() {
    return `${this.baseUrl}/agent/${this.agent.id}`;
  }

  // The sidebar is open by default; the chosen section renders inside the form.
  async openSection(name: string): Promise<Locator> {
    await this.configuration.getByRole("menuitem", { name }).click();
    await expect(
      this.configuration.getByRole("heading", { name })
    ).toBeVisible();
    return this.configuration.locator(".agent-configuration__body");
  }

  // The body predicate tells a debounced save apart from an earlier one.
  waitForTriggerResponse(
    method: string,
    matches: (body: any) => boolean = () => true
  ): Promise<Response> {
    const prefix = `/api/agent/${this.agent.id}/triggers/`;
    return this.page.waitForResponse(async (response) => {
      if (
        response.request().method() !== method ||
        !response.url().includes(prefix)
      ) {
        return false;
      }
      if (response.status() === 204) return true;
      try {
        return matches(await response.json());
      } catch {
        return false;
      }
    });
  }
}
