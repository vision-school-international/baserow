<template>
  <div class="decorator-item">
    <img class="decorator-item__image" :src="decoratorType.getImage()" />
    <div class="decorator-item__content">
      <div class="decorator-item__title">
        {{ decoratorType.getName() }}
      </div>
      <div class="decorator-item__description">
        {{ decoratorType.getDescription() }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ViewDecoratorItem',
  props: {
    decoratorType: {
      type: Object,
      required: true,
    },
  },
}
</script>
