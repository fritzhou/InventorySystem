import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'
import { AuthProvider, useAuth, type AuthUser } from './auth'
import { api } from './services/api'

const user=(role:'ADMIN'|'MANAGER'|'CASHIER',must=false):AuthUser=>({id:role,email:`${role.toLowerCase()}@example.com`,display_name:`Test ${role}`,role,is_active:true,must_change_password:must,created_at:'2026-01-01',last_login_at:null})
const json=(value:unknown,status=200)=>new Response(status===204?null:JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}})
afterEach(()=>{cleanup();vi.restoreAllMocks();window.history.replaceState({},'','/login')})

test('initializes authentication and renders login after me returns 401',async()=>{
  window.history.replaceState({},'','/dashboard')
  vi.spyOn(globalThis,'fetch').mockResolvedValue(json({detail:'Authentication required'},401))
  render(<AuthProvider><App/></AuthProvider>)
  expect(screen.getByText('Loading StockFlow…')).toBeInTheDocument()
  expect(await screen.findByRole('button',{name:'Sign In'})).toBeInTheDocument()
})

test('failed login shows generic error and does not emit session expiration',async()=>{
  const expired=vi.fn();window.addEventListener('stockflow:session-expired',expired)
  vi.spyOn(globalThis,'fetch').mockResolvedValue(json({detail:'Invalid email or password'},401))
  render(<AuthProvider><App/></AuthProvider>);await screen.findByRole('button',{name:'Sign In'})
  fireEvent.change(screen.getByLabelText('Email'),{target:{value:'bad@example.com'}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'wrong-password'}});fireEvent.click(screen.getByRole('button',{name:'Sign In'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password');expect(expired).not.toHaveBeenCalled()
  window.removeEventListener('stockflow:session-expired',expired)
})

test.each([['ADMIN',false,'/dashboard','Dashboard'],['MANAGER',false,'/pos','Point of Sale'],['CASHIER',false,'/pos','Point of Sale'],['CASHIER',true,'/account','Account']] as const)('successful %s login uses an allowed landing page',async(role,mustChange,landing,heading)=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(json({detail:'Authentication required'},401)).mockResolvedValueOnce(json(user(role,mustChange)))
  render(<AuthProvider><App/></AuthProvider>);await screen.findByRole('button',{name:'Sign In'})
  fireEvent.change(screen.getByLabelText('Email'),{target:{value:`${role.toLowerCase()}@example.com`}});fireEvent.change(screen.getByLabelText('Password'),{target:{value:'valid-password'}});fireEvent.click(screen.getByRole('button',{name:'Sign In'}))
  await waitFor(()=>expect(window.location.pathname).toBe(landing));expect(await screen.findByRole('heading',{name:heading})).toBeInTheDocument()
})

function Probe(){const {user,logout}=useAuth();return <><span>{user?.role??'signed-out'}</span><button onClick={()=>void logout()}>Log out</button></>}
test('protected 401 clears auth while 403 does not',async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(json(user('ADMIN'))).mockResolvedValueOnce(json({detail:'Forbidden'},403)).mockResolvedValueOnce(json({detail:'Expired'},401))
  render(<AuthProvider><Probe/></AuthProvider>);expect(await screen.findByText('ADMIN')).toBeInTheDocument()
  await expect(api.getExpenses()).rejects.toMatchObject({status:403});expect(screen.getByText('ADMIN')).toBeInTheDocument()
  await expect(api.getExpenses()).rejects.toMatchObject({status:401});await waitFor(()=>expect(screen.getByText('signed-out')).toBeInTheDocument())
})

test('expired protected request renders the login page',async()=>{
  window.history.replaceState({},'','/account')
  vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(json(user('ADMIN'))).mockResolvedValueOnce(json({detail:'Expired'},401))
  render(<AuthProvider><App/></AuthProvider>);expect(await screen.findByRole('heading',{name:'Account'})).toBeInTheDocument()
  await expect(api.getExpenses()).rejects.toMatchObject({status:401})
  expect(await screen.findByRole('button',{name:'Sign In'})).toBeInTheDocument();expect(window.location.pathname).toBe('/login')
})

test('logout clears the authenticated user',async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(json(user('ADMIN'))).mockResolvedValueOnce(json(null,204))
  render(<AuthProvider><Probe/></AuthProvider>);expect(await screen.findByText('ADMIN')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Log out'}));await waitFor(()=>expect(screen.getByText('signed-out')).toBeInTheDocument())
})

test.each([['CASHIER',['Point of Sale','Sales History'],['Expenses','Reports','Users','Audit Log']],['MANAGER',['Products','Purchase Orders','Suppliers'],['Expenses','Reports','Users','Audit Log']],['ADMIN',['Dashboard','Expenses','Reports','Users','Audit Log'],[]]] as const)('shows %s navigation',async(role,visible,hidden)=>{
  window.history.replaceState({},'','/pos');vi.spyOn(globalThis,'fetch').mockResolvedValue(json(user(role)))
  render(<AuthProvider><App/></AuthProvider>);for(const label of visible)expect(await screen.findByRole('link',{name:label})).toBeInTheDocument();for(const label of hidden)expect(screen.queryByRole('link',{name:label})).not.toBeInTheDocument()
})

test('must-change-password redirects to account',async()=>{
  window.history.replaceState({},'','/pos');vi.spyOn(globalThis,'fetch').mockResolvedValue(json(user('CASHIER',true)))
  render(<AuthProvider><App/></AuthProvider>);await waitFor(()=>expect(window.location.pathname).toBe('/account'))
})

test('application shell exposes accessible responsive navigation controls',async()=>{
  window.history.replaceState({},'','/pos');vi.spyOn(globalThis,'fetch').mockResolvedValue(json(user('CASHIER')))
  render(<AuthProvider><App/></AuthProvider>);expect(await screen.findByRole('navigation',{name:'Main navigation'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Open navigation'}));expect(screen.getByRole('button',{name:'Close navigation'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Close navigation'}));expect(screen.getByRole('link',{name:'StockFlow home'})).toBeInTheDocument()
})
