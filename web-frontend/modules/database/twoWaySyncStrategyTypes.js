import { Registerable } from '@baserow/modules/core/registry'

export class TwoWaySyncStrategyType extends Registerable {
  /**
   * Should return a human-readable description how the two-way sync strategy works.
   */
  getDescription() {
    throw new Error(
      'The description of a two way sync strategy type must be set.'
    )
  }

  constructor(...args) {
    super(...args)
    this.type = this.getType()
  }

  serialize() {
    return {
      type: this.type,
    }
  }
}
