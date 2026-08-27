export type ExpenseStatus = 'ACTIVE' | 'VOIDED'
export interface ExpenseCategory { id:string; name:string; description:string|null; is_active:boolean; created_at:string; updated_at:string }
export interface Expense { id:string; expense_number:string; category_id:string; category_name:string; description:string; amount:string; expense_date:string; notes:string|null; status:ExpenseStatus; created_at:string; updated_at:string; voided_at:string|null; void_reason:string|null }
export interface ExpenseInput { category_id:string; description:string; amount:string; expense_date:string; notes?:string|null }
export interface ExpensePage { items:Expense[]; total:number; page:number; page_size:number; pages:number }
export interface ExpenseSummary { total_expenses:string; expense_count:number; categories:Array<{category:string;amount:string}> }
