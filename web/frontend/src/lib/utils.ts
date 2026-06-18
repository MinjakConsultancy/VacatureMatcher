import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(d: string | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("nl-NL");
}

export function deadlineBadgeClass(d: string | null | undefined): string {
  if (!d) return "bg-muted text-muted-foreground";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(d);
  dl.setHours(0, 0, 0, 0);
  if (dl <= today) return "bg-red-100 text-red-800";
  const diff = (dl.getTime() - today.getTime()) / 86400000;
  if (diff <= 7) return "bg-amber-100 text-amber-900";
  return "bg-emerald-100 text-emerald-900";
}
