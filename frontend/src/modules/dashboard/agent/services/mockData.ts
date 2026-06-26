import type { Role } from "@/app/store/authStore";

export interface AgentKPI {
  headCount: number;
  presentCount: number;
  lateLogin: number;
  earlyLogout: number;
  shiftAdherence: number;
  nonAdherence: number;
  plannedShrinkage: number;
  unplannedShrinkage: number;
  overallShrinkage: number;
  attrition: number;
  totalCalls: number;
  connectedCalls: number;
  notConnectedCalls: number;
  positiveCalls: number;
  talkTime: number;
  loginHours: number;
  totalLogin: number;
  staffTime: number;
  downtime: number;
  idleTime: number;
  breakTime: number;
  productivity: number;
}

export const agentKpi: AgentKPI = {
  headCount: 248, presentCount: 221, lateLogin: 12, earlyLogout: 8,
  shiftAdherence: 92.4, nonAdherence: 7.6, plannedShrinkage: 6.2, unplannedShrinkage: 4.1,
  overallShrinkage: 10.3, attrition: 3.4, totalCalls: 18420, connectedCalls: 15210, notConnectedCalls: 3210,
  positiveCalls: 4720, talkTime: 642, loginHours: 1820, totalLogin: 1985, staffTime: 1740,
  downtime: 38, idleTime: 92, breakTime: 178, productivity: 87.6,
};

export const supportKpi = {
  headCount: 142, presentCount: 130, lateLogin: 6, earlyLogout: 4,
  adherence: 94.1, nonAdherence: 5.9, breakHours: 124, loginHours: 1042,
  downtime: 18, idleTime: 56, shrinkage: 8.7, attrition: 2.1,
};

export function generateTrend(days = 14, base: number, variance = 0.2) {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return { date: `${d.getDate()}/${d.getMonth() + 1}`, value: Math.round(base * (1 + (Math.random() - 0.5) * variance)) };
  });
}

export function performanceTrend(days = 14) {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    const total = 1200 + Math.round(Math.random() * 400);
    const connected = Math.round(total * (0.78 + Math.random() * 0.1));
    const positive = Math.round(connected * (0.28 + Math.random() * 0.08));
    return { date: `${d.getDate()}/${d.getMonth() + 1}`, totalCalls: total, connectedCalls: connected, positiveCalls: positive };
  });
}

export function productivityTrend(days = 14) {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return {
      date: `${d.getDate()}/${d.getMonth() + 1}`,
      productivity: Math.round(80 + Math.random() * 15),
      talkTime: Math.round(40 + Math.random() * 20),
      loginHours: Math.round(110 + Math.random() * 30),
    };
  });
}

export function adherenceTrend(days = 14) {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    const ad = 85 + Math.random() * 10;
    return { date: `${d.getDate()}/${d.getMonth() + 1}`, adherence: Math.round(ad), nonAdherence: Math.round(100 - ad) };
  });
}

export function shrinkageTrend(days = 14) {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    const planned = 4 + Math.random() * 4;
    const unplanned = 2 + Math.random() * 4;
    return {
      date: `${d.getDate()}/${d.getMonth() + 1}`,
      planned: +planned.toFixed(1),
      unplanned: +unplanned.toFixed(1),
      overall: +(planned + unplanned).toFixed(1),
    };
  });
}

export const topPerformers = Array.from({ length: 8 }).map((_, i) => ({
  empId: `EMP${1001 + i}`,
  name: ["Aarav Sharma", "Sneha Rao", "Vikram Singh", "Pooja Mehta", "Karan Bhatia", "Ritika Sen", "Anil Joshi", "Meera Pillai"][i],
  totalCalls: 1100 - i * 35,
  productivity: 96 - i * 1.2,
  positive: 280 - i * 12,
}));

export const lowPerformers = Array.from({ length: 6 }).map((_, i) => ({
  empId: `EMP${2001 + i}`,
  name: ["Rakesh Yadav", "Sunita Bose", "Manoj Tiwari", "Asha Patel", "Vivek Naidu", "Geeta Menon"][i],
  totalCalls: 380 + i * 25,
  productivity: 62 - i * 1.5,
}));

export function visibleManagerFor(role: Role, fullName: string): string | undefined {
  return role === "MANAGER" ? fullName : undefined;
}
