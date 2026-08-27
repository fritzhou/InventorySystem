export interface Category {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface CategoryInput {
  name: string
  description: string | null
}
