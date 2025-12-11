"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Check, X, UserPlus, Loader2, Shield, ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api/client";
import type { UserResponse, UserInviteRequest } from "@/lib/api/admin";

export function AdminUserManagement() {
  const [pendingUsers, setPendingUsers] = useState<UserResponse[]>([]);
  const [allUsers, setAllUsers] = useState<UserResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
  const [inviteData, setInviteData] = useState<UserInviteRequest>({
    name: "",
    email: "",
  });
  const [isInviting, setIsInviting] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const [pending, all] = await Promise.all([
        apiClient.admin.getPendingUsers(),
        apiClient.admin.getAllUsers(),
      ]);
      setPendingUsers(pending);
      setAllUsers(all);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to load users";
      toast.error("Failed to load users", {
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async (userId: string) => {
    try {
      await apiClient.admin.approveUser(userId);
      toast.success("User approved");
      fetchUsers();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to approve user";
      toast.error("Failed to approve user", {
        description: errorMessage,
      });
    }
  };

  const handleReject = async (userId: string) => {
    try {
      await apiClient.admin.rejectUser(userId);
      toast.success("User rejected");
      fetchUsers();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to reject user";
      toast.error("Failed to reject user", {
        description: errorMessage,
      });
    }
  };

  const handleInvite = async () => {
    if (!inviteData.name || !inviteData.email) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      setIsInviting(true);
      await apiClient.admin.inviteUser(inviteData);
      toast.success("User invited successfully");
      setIsInviteDialogOpen(false);
      setInviteData({ name: "", email: "" });
      fetchUsers();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to invite user";
      toast.error("Failed to invite user", {
        description: errorMessage,
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handlePromote = async (userId: string) => {
    try {
      await apiClient.admin.promoteUser(userId);
      toast.success("User promoted to admin");
      fetchUsers();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to promote user";
      toast.error("Failed to promote user", {
        description: errorMessage,
      });
    }
  };

  const handleDemote = async (userId: string) => {
    if (
      !confirm(
        "Are you sure you want to demote this user? They will lose admin privileges."
      )
    ) {
      return;
    }

    try {
      await apiClient.admin.demoteUser(userId);
      toast.success("User demoted to regular user");
      fetchUsers();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to demote user";
      toast.error("Failed to demote user", {
        description: errorMessage,
      });
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge className="bg-green-500">Approved</Badge>;
      case "pending":
        return <Badge className="bg-yellow-500">Pending</Badge>;
      case "rejected":
        return <Badge className="bg-red-500">Rejected</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "admin":
        return (
          <Badge variant="outline" className="border-blue-500 text-blue-700">
            <Shield className="mr-1 h-3 w-3" />
            Admin
          </Badge>
        );
      case "user":
        return <Badge variant="outline">User</Badge>;
      default:
        return <Badge variant="outline">{role}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Pending Users Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Pending Users</CardTitle>
              <CardDescription>
                Users waiting for approval ({pendingUsers.length})
              </CardDescription>
            </div>
            <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Invite User
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite New User</DialogTitle>
                  <DialogDescription>
                    Invite a new user to the system. They will receive a
                    temporary password and need to change it on first login.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={inviteData.name}
                      onChange={(e) =>
                        setInviteData({ ...inviteData, name: e.target.value })
                      }
                      placeholder="John Doe"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={inviteData.email}
                      onChange={(e) =>
                        setInviteData({ ...inviteData, email: e.target.value })
                      }
                      placeholder="user@northeastern.edu"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setIsInviteDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleInvite} disabled={isInviting}>
                    {isInviting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Inviting...
                      </>
                    ) : (
                      "Invite User"
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {pendingUsers.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No pending users
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingUsers.map((user) => (
                  <TableRow key={user.user_id}>
                    <TableCell className="font-medium">{user.name}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{getRoleBadge(user.role)}</TableCell>
                    <TableCell>{getStatusBadge(user.status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleApprove(user.user_id)}
                          className="text-green-600 hover:text-green-700"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReject(user.user_id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* All Users Card */}
      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
          <CardDescription>
            Complete list of all users in the system ({allUsers.length})
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Approved At</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allUsers.map((user) => (
                <TableRow key={user.user_id}>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{getRoleBadge(user.role)}</TableCell>
                  <TableCell>{getStatusBadge(user.status)}</TableCell>
                  <TableCell>
                    {user.approved_at
                      ? new Date(user.approved_at).toLocaleDateString()
                      : "-"}
                  </TableCell>
                  <TableCell>
                    {user.status === "approved" && (
                      <div className="flex items-center gap-2">
                        {user.role === "user" ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePromote(user.user_id)}
                            className="text-blue-600 hover:text-blue-700"
                            title="Promote to Admin"
                          >
                            <Shield className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDemote(user.user_id)}
                            className="text-orange-600 hover:text-orange-700"
                            title="Demote to User"
                          >
                            <ShieldOff className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

