import { useEffect, type ReactElement } from 'react'
import { AppShell, type NavigationItem } from './components/AppShell'
import { navigate, usePathname } from './navigation'
import { ProductsPage } from './pages/ProductsPage';import { PosPage } from './pages/PosPage';import { SalesHistoryPage } from './pages/SalesHistoryPage';import { InventoryHistoryPage } from './pages/InventoryHistoryPage';import { DashboardPage } from './pages/DashboardPage';import { ReportsPage } from './pages/ReportsPage';import { SuppliersPage } from './pages/SuppliersPage';import { PurchaseOrdersPage } from './pages/PurchaseOrdersPage';import { ReturnsPage } from './pages/ReturnsPage';import { ExpensesPage } from './pages/ExpensesPage';import { LoginPage } from './pages/LoginPage';import { UsersPage } from './pages/UsersPage';import { AuditLogPage } from './pages/AuditLogPage';import { AccountPage } from './pages/AccountPage';import { useAuth,type Role } from './auth';import './styles.css'

const routes:Record<string,{roles:Role[];label:string;view:()=>ReactElement}>={
  '/dashboard':{roles:['ADMIN'],label:'Dashboard',view:DashboardPage}, '/':{roles:['ADMIN','MANAGER'],label:'Products',view:ProductsPage},
  '/pos':{roles:['ADMIN','MANAGER','CASHIER'],label:'Point of Sale',view:PosPage}, '/sales':{roles:['ADMIN','MANAGER','CASHIER'],label:'Sales History',view:SalesHistoryPage},
  '/returns':{roles:['ADMIN','MANAGER'],label:'Returns',view:ReturnsPage}, '/inventory':{roles:['ADMIN','MANAGER'],label:'Inventory History',view:InventoryHistoryPage},
  '/expenses':{roles:['ADMIN'],label:'Expenses',view:ExpensesPage}, '/reports':{roles:['ADMIN'],label:'Reports',view:ReportsPage},
  '/purchase-orders':{roles:['ADMIN','MANAGER'],label:'Purchase Orders',view:PurchaseOrdersPage}, '/suppliers':{roles:['ADMIN','MANAGER'],label:'Suppliers',view:SuppliersPage},
  '/users':{roles:['ADMIN'],label:'Users',view:UsersPage}, '/audit-log':{roles:['ADMIN'],label:'Audit Log',view:AuditLogPage},
  '/account':{roles:['ADMIN','MANAGER','CASHIER'],label:'Account',view:AccountPage},
}
const groups:Record<string,NavigationItem['group']>={'/expenses':'finance','/reports':'finance','/users':'management','/audit-log':'management'}
const navigationItems:NavigationItem[]=Object.entries(routes).filter(([path])=>path!=='/account').map(([path,route])=>({path,label:route.label,roles:route.roles,group:groups[path]??'main'}))
export default function App(){const {user,loading,logout}=useAuth();const path=usePathname();if(loading)return <main className="loading-screen">Loading StockFlow…</main>;if(!user)return path==='/login'?<LoginPage/>:<Redirect to="/login"/>;if(path==='/login')return <Redirect to={user.must_change_password?'/account':user.role==='ADMIN'?'/dashboard':'/pos'}/>;if(user.must_change_password&&path!=='/account')return <Redirect to="/account"/>;const normalized=path.startsWith('/purchase-orders')?'/purchase-orders':path;const route=routes[normalized];if(!route||!route.roles.includes(user.role))return <div className="auth-page"><section className="auth-card"><h1>Access denied</h1><p>You do not have permission to view this screen.</p><a href="/pos">Return to Point of Sale</a></section></div>;const View=route.view;return <AppShell user={user} activePath={normalized} items={navigationItems} onLogout={()=>void logout()}><View/></AppShell>}
function Redirect({to}:{to:string}){useEffect(()=>navigate(to),[to]);return <main className="loading-screen">Redirecting…</main>}
