"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { authService } from "@/lib/api";
import { User } from "@/types";
import { FileText, LogOut, ShieldCheck, Sparkles, User as UserIcon } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setUser(authService.getSavedUser());
  }, [pathname]);

  const handleLogout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-800 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 shadow-md">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-white">AdaptiveDocAI</span>
            <span className="ml-2 rounded border border-blue-500/30 bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">
              M.Tech Research
            </span>
          </div>
        </Link>

        <nav className="flex items-center space-x-6 text-sm font-medium">
          {user ? (
            <>
              <Link
                href="/dashboard"
                className={`transition-colors hover:text-white ${
                  pathname === "/dashboard" ? "text-blue-400" : "text-gray-400"
                }`}
              >
                Documents
              </Link>
              <Link
                href="/chat"
                className={`transition-colors hover:text-white ${
                  pathname === "/chat" ? "text-blue-400" : "text-gray-400"
                }`}
              >
                Q&A Chat
              </Link>
              <div className="flex items-center space-x-3 border-l border-gray-800 pl-6">
                <div className="flex items-center space-x-2 rounded-full border border-gray-800 bg-surface px-3 py-1 text-xs text-gray-300">
                  <UserIcon className="h-3.5 w-3.5 text-blue-400" />
                  <span>{user.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 rounded-lg px-2.5 py-1.5 text-xs text-gray-400 transition hover:bg-red-500/10 hover:text-red-400"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center space-x-3">
              <Link
                href="/login"
                className="rounded-lg px-4 py-2 text-sm text-gray-300 transition hover:text-white"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-500"
              >
                Get Started
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}

