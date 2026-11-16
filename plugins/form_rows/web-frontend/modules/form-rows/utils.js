import moment from '@baserow/modules/core/moment'

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

function cellText(cell) {
  return cell.chips
    ? cell.chips.map((chip) => chip.value).join(', ')
    : cell.text
}

// Dates arrive as ISO 8601 in UTC (DRF DateTimeField/DateField, TIME_ZONE "UTC"),
// so as text they sort in time order.
const DATE_TYPES = ['date', 'created_on', 'last_modified']

const NUMBER_TYPES = ['number', 'rating', 'autonumber', 'count', 'link_row']

/** How the "Sort by" list words a column's two directions. */
export function sortKind(field) {
  if (DATE_TYPES.includes(field.type)) return 'date'
  return NUMBER_TYPES.includes(field.type) ? 'number' : 'text'
}

/**
 * What a cell sorts by: its real time for dates, its value for numbers (DRF
 * DecimalField sends strings) and link counts, else the text it shows. null =
 * empty, always last.
 */
export function sortKey(field, value, cell) {
  if (value === null || value === undefined || value === '') return null
  // Parsed, not compared as text: DRF's isoformat() drops microseconds when 0
  // (rest_framework/fields.py DateTimeField.to_representation).
  // Parsed the way core shows these values (fieldTypes.js:2582 moment.utc), so
  // the 6-digit fraction works in every browser.
  if (DATE_TYPES.includes(field.type)) {
    return { number: moment.utc(value).valueOf() }
  }
  const number = typeof value === 'number' ? value : Number(value)
  if (typeof value !== 'object' && !Number.isNaN(number)) return { number }
  const text = cellText(cell)
  return text === '' ? null : { text }
}

function compareKeys(a, b) {
  if (a.number !== undefined && b.number !== undefined) {
    return a.number - b.number
  }
  const left = a.text ?? String(a.number)
  const right = b.text ?? String(b.number)
  return left.localeCompare(right, undefined, { numeric: true })
}

/**
 * The rows shown: those where any cell's shown text contains the search (any
 * case), sorted by column `sort.index`; null keeps the view's own order.
 */
export function visibleRows(rows, fields, search, sort) {
  const query = search.trim().toLowerCase()
  const shown = query
    ? rows.filter((row) =>
        row.cells.some((cell) => cellText(cell).toLowerCase().includes(query))
      )
    : rows
  if (sort.index === null) return shown
  const field = fields[sort.index]
  // The columns changed (another list view) since the sort was picked.
  if (!field) return shown
  const keyed = shown.map((row) => ({
    row,
    key: sortKey(field, row.values[`field_${field.id}`], row.cells[sort.index]),
  }))
  keyed.sort((a, b) => {
    if (a.key === null || b.key === null) {
      return (a.key === null) - (b.key === null)
    }
    const order = compareKeys(a.key, b.key)
    return sort.desc ? -order : order
  })
  return keyed.map((item) => item.row)
}
