"use client";

import { Bell, Settings } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/lib/store/authStore";

export function DashboardHeader() {
  const { user, logout } = useAuthStore();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6 py-10">
      {/* Logo */}
      <Link href="/dashboard" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
        <Image src="/logo.svg" alt="icon" width={190} height={20} />
      </Link>

      {/* Right Side - Notifications, Settings, User */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5" />
        </Button>

        {/* Settings */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/dashboard/settings")}
        >
          <Settings className="h-5 w-5" />
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2 h-auto py-2 px-3">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.avatar} />
                <AvatarFallback>
                  {user?.name?.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="font-medium">{user?.name}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span>{user?.name || "User"}</span>
                {mounted && user?.email && (
                  <span className="text-xs text-muted-foreground font-normal">
                    {user.email}
                  </span>
                )}
                {mounted && user?.role === "admin" && (
                  <span className="text-xs text-blue-600 font-medium mt-1">
                    Administrator
                  </span>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-600">
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
