import { useState, type FormEvent } from 'react'

interface CategoryFormProps {
  isSaving: boolean
  error: string | null
  onSubmit: (name: string, description: string) => Promise<boolean>
}

export function CategoryForm({ isSaving, error, onSubmit }: CategoryFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const created = await onSubmit(name.trim(), description.trim())
    if (created) {
      setName('')
      setDescription('')
    }
  }

  return (
    <form className="category-form" onSubmit={submit}>
      <label>Category name<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Description <span className="optional">optional</span><input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="button secondary" disabled={isSaving}>{isSaving ? 'Adding…' : 'Add category'}</button>
    </form>
  )
}
