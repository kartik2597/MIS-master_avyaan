import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";

interface FiltersProps {
  processes?: string[];
  managers?: string[];
  employees?: string[];
  managerLocked?: string;
}

const DEFAULT_PROCESSES = ["All", "Inbound Sales", "Outbound Sales", "Customer Support", "Collections"];
const DEFAULT_MANAGERS = ["All", "Rohit Kapoor", "Priya Nair", "Suresh Iyer", "Anita Desai"];
const DEFAULT_EMPLOYEES = ["All", "Amit Kumar", "Sneha Rao", "Vikram Singh", "Pooja Mehta"];

export function DashboardFilters({
  processes = DEFAULT_PROCESSES,
  managers = DEFAULT_MANAGERS,
  employees = DEFAULT_EMPLOYEES,
  managerLocked,
}: FiltersProps) {
  return (
    <Card className="p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        <div className="space-y-1.5">
          <Label className="text-xs">Date Range</Label>
          <Input type="date" defaultValue="2026-06-01" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">To</Label>
          <Input type="date" defaultValue="2026-06-22" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Process</Label>
          <Select defaultValue="All">
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {processes.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Manager</Label>
          <Select defaultValue={managerLocked ?? "All"} disabled={!!managerLocked}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {(managerLocked ? [managerLocked] : managers).map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2">
          <div className="flex-1 space-y-1.5">
            <Label className="text-xs">Employee</Label>
            <Select defaultValue="All">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {employees.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" size="icon" className="shrink-0" title="Reset filters">
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
