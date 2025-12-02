import { BaseAPI } from "./base";

export interface User {
  id: string;
  email: string;
  name: string;
  role?: string;
  status?: string;
  avatar?: string;
}

export interface AuthResponse {
  message: string;
  user: User;
}

export class AuthAPI extends BaseAPI {
  async login(email: string, password: string): Promise<AuthResponse> {
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    return this.request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
  }

  async signup(
    name: string,
    email: string,
    password: string,
  ): Promise<AuthResponse> {
    return this.request("/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
  }

  async logout(): Promise<{ message: string }> {
    return this.request("/auth/logout", { method: "POST" });
  }

  async me(): Promise<User> {
    return this.request("/auth/me");
  }

  async getApprovedUsers(): Promise<UserResponse[]> {
    return this.request("/auth/users/approved", {
      method: "GET",
    });
  }
}

export interface UserResponse {
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: string;
}
