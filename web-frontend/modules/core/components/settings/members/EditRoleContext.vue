<template>
  <Context ref="context" overflow-scroll max-height-if-outside-viewport>
    <template v-if="Object.keys(subject).length > 0">
      <div class="context__menu-title">
        {{ $t('membersSettings.membersTable.columns.role') }}
      </div>
      <ul class="context__menu context__menu--can-be-active">
        <li
          v-for="(role, index) in visibleRoles"
          :key="index"
          class="context__menu-item"
        >
          <a
            class="context__menu-item-link context__menu-item-link--with-desc"
            :class="{ active: subject[roleValueColumn] === role.uid }"
            @click="roleUpdate(role.uid, subject)"
          >
            <span class="context__menu-item-title">
              {{ role.name }}
            </span>
            <div v-if="role.description" class="context__menu-item-description">
              {{ role.description }}
            </div>
            <i
              v-if="subject[roleValueColumn] === role.uid"
              class="context__menu-active-icon iconoir-check"
            ></i>
          </a>
        </li>
        <li
          v-if="allowRemovingRole"
          class="context__menu-item context__menu-item--with-separator"
        >
          <a
            class="context__menu-item-link context__menu-item-link--delete"
            @click="$emit('delete')"
            >{{ $t('action.remove') }}</a
          >
        </li>
      </ul>
    </template>
  </Context>
</template>

<script>
import context from '@baserow/modules/core/mixins/context'

export default {
  name: 'EditRoleContext',
  mixins: [context],
  props: {
    workspace: {
      type: Object,
      required: true,
    },
    subject: {
      required: true,
      type: Object,
    },
    roles: {
      required: true,
      type: Array,
    },
    roleValueColumn: {
      type: String,
      required: false,
      default: 'permissions',
    },
    allowRemovingRole: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['delete', 'update-role'],
  computed: {
    visibleRoles() {
      return this.roles.filter((role) => role.isVisible)
    },
  },
  methods: {
    roleUpdate(roleNew, subject) {
      if (subject[this.roleValueColumn] === roleNew) {
        return
      }

      this.$emit('update-role', { uid: roleNew, subject })
      this.hide()
    },
  },
}
</script>
