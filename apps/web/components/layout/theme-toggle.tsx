"use client";
import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
const subscribe = () => () => {};
export function ThemeToggle() {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const { theme, resolvedTheme, setTheme } = useTheme();
  const Icon = mounted && resolvedTheme === "dark" ? Moon : Sun;
  return <DropdownMenu><DropdownMenuTrigger asChild>
    <Button variant="ghost" size="icon" aria-label="Choose color theme" className="size-11 rounded-control bg-surface-2"><Icon size={20} strokeWidth={1.75} aria-hidden="true"/></Button>
  </DropdownMenuTrigger><DropdownMenuContent align="end" className="min-w-44">
    <DropdownMenuLabel>Appearance</DropdownMenuLabel>
    <DropdownMenuRadioGroup value={mounted ? theme : "system"} onValueChange={setTheme}>
      <DropdownMenuRadioItem value="light"><Sun aria-hidden="true"/>Light</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="dark"><Moon aria-hidden="true"/>Dark</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="system"><Monitor aria-hidden="true"/>System</DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  </DropdownMenuContent></DropdownMenu>;
}
