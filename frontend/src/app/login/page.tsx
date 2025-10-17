"use client";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/store/authStore";

export default function Login() {
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const handleLogin = async () => {
    try {
      await login("hello", "test");
      console.log("successfull");
    } catch (error) {
      console.error("Login failed");
    }
  };

  const handleLogout = () => {
    try {
      logout();
      console.log("successfull");
    } catch (error) {
      console.error("Logout failed");
    }
  };

  return (
    <>
      {user ? (
        <div>
          <p> Email: {user.email}</p>
          <p> Id: {user.id}</p>
          <p> Name: {user.name}</p>
        </div>
      ) : (
        <Button onClick={handleLogin}>Click to login</Button>
      )}
      <Button onClick={handleLogout}>Click to Logout</Button>
    </>
  );
}
