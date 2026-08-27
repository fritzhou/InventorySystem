export const formatMoney = (value: string) => {
  const [whole = '0', fraction = ''] = value.split('.')
  const normalized = whole.replace(/^(-?)0+(?=\d)/, '$1')
  return `₱${normalized.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction.padEnd(2, '0').slice(0, 2)}`
}
