import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'

import { ErrorState, Pagination, SkeletonRows } from './ui'

/**
 * One table for every list page.
 *
 * `columns` entries: { key, header, sortable, align, render(row), className }
 */
export default function DataTable({
  columns,
  rows,
  loading,
  error,
  onRetry,
  empty,
  sortBy,
  sortOrder,
  onSort,
  meta,
  page,
  onPage,
  pageSize,
  onPageSize,
  footer,
  caption,
  rowKey = (row) => row.id,
}) {
  if (error) {
    return (
      <div style={{ padding: 14 }}>
        <ErrorState error={error} onRetry={onRetry} />
      </div>
    )
  }

  if (loading && !rows.length) return <SkeletonRows rows={6} />

  if (!loading && !rows.length) return empty ?? null

  return (
    <>
      <div className="table-wrap">
        <table className="data">
          {caption && <caption className="visually-hidden">{caption}</caption>}
          <thead>
            <tr>
              {columns.map((column) => {
                const isSorted = sortBy === column.key
                const SortIcon = !isSorted ? ChevronsUpDown : sortOrder === 'asc' ? ArrowUp : ArrowDown
                return (
                  <th
                    key={column.key}
                    className={`${column.align === 'right' ? 'num' : ''} ${
                      column.sortable && onSort ? 'sortable' : ''
                    }`.trim()}
                    onClick={column.sortable && onSort ? () => onSort(column.key) : undefined}
                    aria-sort={isSorted ? (sortOrder === 'asc' ? 'ascending' : 'descending') : undefined}
                    scope="col"
                  >
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                        justifyContent: column.align === 'right' ? 'flex-end' : 'flex-start',
                        width: '100%',
                      }}
                    >
                      {column.header}
                      {column.sortable && onSort && <SortIcon size={13} aria-hidden="true" />}
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody style={loading ? { opacity: 0.55 } : undefined}>
            {rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`${column.align === 'right' ? 'num' : ''} ${column.className || ''}`.trim()}
                  >
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {footer && <tfoot>{footer}</tfoot>}
        </table>
      </div>
      {meta && onPage && (
        <Pagination meta={meta} page={page} onPage={onPage} pageSize={pageSize} onPageSize={onPageSize} />
      )}
    </>
  )
}
