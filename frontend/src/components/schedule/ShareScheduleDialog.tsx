"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Share2, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiClient } from "@/lib/api/client";
import type { UserResponse } from "@/lib/api/auth";
import type { ScheduleShare } from "@/lib/api/schedules";

interface ShareScheduleDialogProps {
  scheduleId: string;
  scheduleName: string;
  onShareUpdate?: () => void;
}

export function ShareScheduleDialog({
  scheduleId,
  scheduleName,
  onShareUpdate,
}: ShareScheduleDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [allUsers, setAllUsers] = useState<UserResponse[]>([]);
  const [shares, setShares] = useState<ScheduleShare[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [isLoadingShares, setIsLoadingShares] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, scheduleId]);

  const fetchData = async () => {
    setIsLoading(true);
    setIsLoadingShares(true);
    try {
      // Fetch approved users and current shares in parallel
      const [users, currentShares] = await Promise.all([
        apiClient.auth.getApprovedUsers(),
        apiClient.schedules.getScheduleShares(scheduleId),
      ]);
      setAllUsers(users);
      setShares(currentShares);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to load data";
      toast.error("Failed to load data", {
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
      setIsLoadingShares(false);
    }
  };

  const handleShare = async () => {
    if (!selectedUserId) {
      toast.error("Please select a user");
      return;
    }

    try {
      setIsSharing(true);
      await apiClient.schedules.shareSchedule(
        scheduleId,
        selectedUserId,
        "view", // All shares are view-only since there's no edit functionality
      );
      toast.success("Schedule shared successfully");
      setSelectedUserId("");
      fetchData();
      onShareUpdate?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to share schedule";
      toast.error("Failed to share schedule", {
        description: errorMessage,
      });
    } finally {
      setIsSharing(false);
    }
  };

  const handleUnshare = async (shareId: string) => {
    try {
      await apiClient.schedules.unshareSchedule(shareId);
      toast.success("Share removed");
      fetchData();
      onShareUpdate?.();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to remove share";
      toast.error("Failed to remove share", {
        description: errorMessage,
      });
    }
  };

  // Filter out users who already have a share
  const availableUsers = allUsers.filter(
    (user) => !shares.some((share) => share.shared_with_user_id === user.user_id),
  );

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Share2 className="mr-2 h-4 w-4" />
          Share
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Share Schedule: {scheduleName}</DialogTitle>
          <DialogDescription>
            Share this schedule with other users. They will be able to view the schedule.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Share Form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="user">Select User</Label>
                <Select
                  value={selectedUserId}
                  onValueChange={setSelectedUserId}
                  disabled={availableUsers.length === 0}
                >
                  <SelectTrigger id="user">
                    <SelectValue placeholder="Choose a user to share with">
                      {selectedUserId &&
                        allUsers.find((u) => u.user_id === selectedUserId)?.name}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {availableUsers.length === 0 ? (
                      <div className="px-2 py-1.5 text-sm text-muted-foreground text-center">
                        No available users
                      </div>
                    ) : (
                      availableUsers.map((user) => (
                        <SelectItem key={user.user_id} value={user.user_id}>
                          <div className="flex flex-col">
                            <span>{user.name}</span>
                            <span className="text-xs text-muted-foreground">
                              {user.email}
                            </span>
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleShare}
                disabled={!selectedUserId || isSharing}
                className="w-full"
              >
                {isSharing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sharing...
                  </>
                ) : (
                  "Share Schedule"
                )}
              </Button>
            </div>

            {/* Current Shares */}
            <div className="space-y-2">
              <Label>Current Shares ({shares.length})</Label>
              {shares.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No shares yet
                </p>
              ) : (
                <div className="border rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>User</TableHead>
                        <TableHead>Shared At</TableHead>
                        <TableHead className="w-[100px]">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {shares.map((share) => (
                        <TableRow key={share.share_id}>
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="font-medium">
                                {share.shared_with_user_name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {share.shared_with_user_email}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {new Date(share.shared_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUnshare(share.share_id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

