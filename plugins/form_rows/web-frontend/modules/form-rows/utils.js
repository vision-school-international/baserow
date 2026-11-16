/**
 * What a listed cell shows: chips for select fields, otherwise the field type's own
 * text (fieldTypes.js toHumanReadableString, which formats dates in the visitor's
 * time zone unless the field forces one). Link fields arrive from the backend as
 * a count and show as "4 passengers".
 */
export function cellDisplay(registry, field, value) {
  if (field.type === 'link_row') {
    return { text: value ? `${value} ${field.name.toLowerCase()}` : '' }
  }
  if (field.type === 'single_select') {
    return { chips: value ? [value] : [] }
  }
  if (field.type === 'multiple_select') {
    return { chips: value || [] }
  }
  const text = registry
    .get('field', field.type)
    .toHumanReadableString(field, value)
  return { text: text === null || text === undefined ? '' : String(text) }
}
