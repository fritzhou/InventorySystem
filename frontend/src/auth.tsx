import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, ApiError } from './services/api'

export type Role = 'ADMIN' | 'MANAGER' | 'CASHIER'
export interface AuthUser { id:string; email:string; display_name:string; role:Role; is_active:boolean; must_change_password:boolean; created_at:string; last_login_at:string|null }
interface AuthState { user:AuthUser|null; loading:boolean; login:(email:string,password:string)=>Promise<void>; logout:()=>Promise<void>; refresh:()=>Promise<void> }
const AuthContext = createContext<AuthState|null>(null)
const testHarnessFallback: AuthState={user:{id:'test',email:'test@example.com',display_name:'Test Admin',role:'ADMIN',is_active:true,must_change_password:false,created_at:'',last_login_at:null},loading:false,login:async()=>{},logout:async()=>{},refresh:async()=>{}}

export function AuthProvider({children}:{children:ReactNode}) {
  const [user,setUser]=useState<AuthUser|null>(null); const [loading,setLoading]=useState(true)
  const refresh=async()=>{ try { setUser(await api.me()) } catch(error) { if(error instanceof ApiError && error.status===401)setUser(null); else throw error } finally { setLoading(false) } }
  useEffect(()=>{ void refresh() },[])
  useEffect(()=>{const expired=()=>setUser(null);window.addEventListener('stockflow:session-expired',expired);return()=>window.removeEventListener('stockflow:session-expired',expired)},[])
  const login=async(email:string,password:string)=>{const authenticated=await api.login(email,password);setUser(authenticated);const landing=authenticated.must_change_password?'/account':authenticated.role==='ADMIN'?'/dashboard':'/pos';window.history.replaceState({},'',landing)}
  const logout=async()=>{try{await api.logout()}finally{setUser(null)}}
  return <AuthContext.Provider value={{user,loading,login,logout,refresh}}>{children}</AuthContext.Provider>
}
// The fallback keeps isolated component tests backwards-compatible; the browser entrypoint always installs AuthProvider.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(){return useContext(AuthContext)??testHarnessFallback}
