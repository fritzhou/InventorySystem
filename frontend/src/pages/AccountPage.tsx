import { useState, type FormEvent } from 'react'
import { api } from '../services/api'
import { useAuth } from '../auth'
import { navigate } from '../navigation'

export function AccountPage(){
  const {user,refresh}=useAuth()
  const [current,setCurrent]=useState('')
  const [next,setNext]=useState('')
  const [confirm,setConfirm]=useState('')
  const [message,setMessage]=useState('')
  const [error,setError]=useState('')
  const [saving,setSaving]=useState(false)
  const required=Boolean(user?.must_change_password)

  async function submit(e:FormEvent){
    e.preventDefault()
    setError('')
    setMessage('')
    if(next!==confirm){setError('New passwords do not match.');return}
    setSaving(true)
    try{
      await api.changePassword(current,next)
      setMessage('Your password was changed successfully.')
      setCurrent('');setNext('');setConfirm('')
      await refresh()
      if(required) navigate(user?.role==='ADMIN'?'/dashboard':'/pos')
    }catch(e){
      setError(e instanceof Error?e.message:'Password could not be changed')
    }finally{setSaving(false)}
  }

  return <section className={required?'account-required':''}>
    <div className="page-heading"><div><span className="eyebrow">Profile & security</span><h1>{required?'Set a new password':'Account'}</h1><p>{required?'Your account is ready. Replace the temporary password before opening StockFlow.':'Review your StockFlow identity and keep your account secure.'}</p></div></div>

    {required&&<section className="password-gate" role="status"><span className="password-gate-icon" aria-hidden="true">✓</span><div><strong>One security step before you continue</strong><p>This cashier account was created with a temporary password. Point of Sale and Sales History will unlock immediately after you choose your own password.</p></div></section>}

    <div className="account-grid">
      <section className="card profile-card"><span className="profile-avatar">{user?.display_name.slice(0,2).toUpperCase()}</span><div><h2>{user?.display_name}</h2><p>{user?.email}</p><span className="status-pill active">{user?.role}</span>{required&&<span className="status-pill password-status">Password setup required</span>}</div></section>
      <form className="card security-card" onSubmit={submit}><span className="eyebrow">Security</span><h2>{required?'Create your password':'Change password'}</h2><p>{required?'Enter the temporary password you just signed in with, then choose a new password with at least 10 characters.':'Use at least 10 characters. You will use the new password the next time you sign in.'}</p><label>{required?'Temporary password':'Current password'}<input autoComplete="current-password" type="password" value={current} onChange={e=>setCurrent(e.target.value)} required/></label><label>New password<input autoComplete="new-password" type="password" minLength={10} value={next} onChange={e=>setNext(e.target.value)} required/></label><label>Confirm new password<input autoComplete="new-password" type="password" minLength={10} value={confirm} onChange={e=>setConfirm(e.target.value)} required/></label>{error&&<p className="error" role="alert">{error}</p>}{message&&<p className="success-note" role="status">{message}</p>}<div className="form-actions"><button className="button primary" disabled={saving}>{saving?(required?'Saving password…':'Changing…'):(required?'Save password & continue':'Change password')}</button></div></form>
    </div>
  </section>
}
