import { BaseAPI } from "./base";

export interface UserResponse {
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  invited_by: string | null;
  invited_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
}

export interface UserInviteRequest {
  name: string;
  email: string;
}

export class AdminAPI extends BaseAPI {
  async getPendingUsers(): Promise<UserResponse[]> {
    return this.request("/admin/users/pending", {
      method: "GET",
    });
  }

  async getAllUsers(): Promise<UserResponse[]> {
    return this.request("/admin/users", {
      method: "GET",
    });
  }

  async approveUser(userId: string): Promise<{ message: string }> {
    return this.request(`/admin/users/${userId}/approve`, {
      method: "POST",
    });
  }

  async rejectUser(userId: string): Promise<{ message: string }> {
    return this.request(`/admin/users/${userId}/reject`, {
      method: "POST",
    });
  }

  async inviteUser(
    data: UserInviteRequest,
  ): Promise<{ message: string; user_id: string }> {
    return this.request("/admin/users/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  async promoteUser(
    userId: string,
  ): Promise<{ message: string; user: UserResponse }> {
    return this.request(`/admin/users/${userId}/promote`, {
      method: "POST",
    });
  }

  async demoteUser(
    userId: string,
  ): Promise<{ message: string; user: UserResponse }> {
    return this.request(`/admin/users/${userId}/demote`, {
      method: "POST",
    });
  }
}
