"use client";

import { MoveLeft, User, Users } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AdminUserManagement } from "@/components/admin/AdminUserManagement";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/authStore";

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  // Get initial tab from URL query parameter, default to "account"
  const initialTab = searchParams.get("tab") || "account";

  useEffect(() => {
    // Verify user is admin
    const verifyAdmin = async () => {
      if (user?.role === "admin") {
        try {
          await apiClient.admin.getPendingUsers();
          setIsAdmin(true);
        } catch (_err) {
          setIsAdmin(false);
        }
      }
      setIsLoading(false);
    };

    verifyAdmin();
  }, [user]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <p className="text-sm text-muted-foreground">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="sm"
          className="rounded-md"
          onClick={() => router.push("/dashboard")}
        >
          <MoveLeft />
          Back
        </Button>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbPage>Settings</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and system preferences
        </p>
      </div>

      <Tabs defaultValue={initialTab} className="w-full">
        <TabsList>
          <TabsTrigger value="account">
            <User className="mr-2 h-4 w-4" />
            Account
          </TabsTrigger>
          {isAdmin && (
            <TabsTrigger value="users">
              <Users className="mr-2 h-4 w-4" />
              User Management
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="account" className="mt-6">
          <div className="rounded-lg border bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Account Settings</h2>
            <p className="text-sm text-muted-foreground">
              Settings and preferences will be available here soon.
            </p>
          </div>
        </TabsContent>

        {isAdmin && (
          <TabsContent value="users" className="mt-6">
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">User Management</h2>
                <p className="text-sm text-muted-foreground">
                  Approve, reject, and invite users to the system
                </p>
              </div>
              <AdminUserManagement />
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <p className="text-sm text-muted-foreground">Loading settings...</p>
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}
