<template>
  <Dropdown v-model="selectedRole" :show-search="false" fixed-items>
    <DropdownItem
      v-for="role in roles"
      :key="role.uid"
      :ref="`role${role.uid}`"
      :name="role.name"
      :value="role.uid"
      :icon="showRoleIcons ? role.icon : null"
      :description="role.description"
    >
      {{ role.name }}
    </DropdownItem>
  </Dropdown>
</template>

<script>
export default {
  name: 'WorkspaceRoleSelector',
  props: {
    showRoleIcons: { type: Boolean, default: false },
    modelValue: {
      type: String,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
    roles: {
      type: Array,
      required: true,
    },
  },
  emits: ['update:modelValue'],
  computed: {
    selectedRole: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      },
    },
  },
}
</script>
