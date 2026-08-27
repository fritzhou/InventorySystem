import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'

const json=(value:unknown)=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}})
const empty: never[]=[];const stock={total_active_products:0,total_units_in_stock:0,low_stock:[],out_of_stock:[]}
function dashboard(summary:Record<string,unknown>){vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{const url=String(input);if(url.includes('sales-trend')||url.includes('top-products'))return json(empty);if(url.includes('inventory-status'))return json(stock);return json(summary)})}
const base={sales_total:'100.00',transaction_count:1,items_sold:1,gross_profit:'40.00',profit_complete:true,operating_expenses:'15.00',net_profit:'25.00',net_profit_complete:true,average_transaction_value:'100.00',total_active_products:0,total_units_in_stock:0,low_stock_count:0,out_of_stock_count:0}
afterEach(()=>{cleanup();vi.restoreAllMocks();window.history.pushState({},'','/')})

test('dashboard displays operating expenses and net profit',async()=>{window.history.pushState({},'','/dashboard');dashboard(base);render(<App/>);expect(await screen.findByText('Operating Expenses')).toBeInTheDocument();expect(screen.getByText('₱15.00')).toBeInTheDocument();expect(screen.getByText('₱25.00')).toBeInTheDocument()})
test('dashboard displays incomplete net profit honestly',async()=>{window.history.pushState({},'','/dashboard');dashboard({...base,profit_complete:false,net_profit:null,net_profit_complete:false});render(<App/>);expect(await screen.findByText('Incomplete historical cost data')).toBeInTheDocument()})
test('dashboard supports negative net profit',async()=>{window.history.pushState({},'','/dashboard');dashboard({...base,operating_expenses:'50.00',net_profit:'-10.00'});render(<App/>);expect(await screen.findByText('₱-10.00')).toBeInTheDocument()})
