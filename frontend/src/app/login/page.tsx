"use client";

import { useAuthStore } from "@/lib/store/authStore";
import { Tabs, TabsTrigger, TabsContent, TabsList } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardContent,
  CardDescription,
  CardFooter,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default function Login() {
  const login = useAuthStore((state) => state.login);
  const user = useAuthStore((state) => state.user);

  const handleLogin = async () => {
    try {
      await login("hello", "test");
      console.log("successful");
    } catch (error) {
      console.error("Login failed", error);
    }
  };

  const handleSignup = async () => {
      const signup = useAuthStore.getState().signup;
  }

  const handleLogout = () => {
    // placeholder - auth store likely has a logout action
    const logout = useAuthStore.getState().logout;
    if (logout) logout();
  };

  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black text-white rounded flex items-center justify-center font-semibold">
            EE
          </div>
          <span className="font-semibold">ExamEngine</span>
        </div>
        <div className="flex items-center gap-4">
          <button className="text-sm text-slate-600">🔔</button>
          <button className="text-sm text-slate-600">⚙️</button>
          <Link href="/login" className="text-sm text-slate-700">
            Sign in
          </Link>
        </div>
      </header>

      {/* Main - centered card */}
      <main className="flex flex-1 items-start justify-center py-12 px-4">
        <div className="w-full max-w-3xl">
          <div className="mx-auto max-w-xl">
            <Tabs defaultValue="signin">
              <TabsList className="mb-4">
                <TabsTrigger value="signin">Sign in</TabsTrigger>
                <TabsTrigger value="signup">Sign up</TabsTrigger>
              </TabsList>

              <TabsContent value="signin">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-2xl">Sign in</CardTitle>
                    <CardDescription>
                      Log in into your account by using correct name and
                      password
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-6">
                    <div className="grid gap-3">
                      <Label htmlFor="name">Name</Label>
                      <Input id="name" defaultValue="Pedro Duarte" />
                    </div>

                    <div className="grid gap-3">
                      <Label htmlFor="password">Password</Label>
                      <Input id="password" type="password" defaultValue="********" />
                    </div>

                    <div className="pt-2">
                      <Button onClick={handleLogin} className="bg-slate-900">
                        Login
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="signup">
                <Card>
                  <CardHeader>
                    <CardTitle>Sign up</CardTitle>
                    <CardDescription>Create an account</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-6">
                    <div className="grid gap-3">
                      <Label htmlFor="su-name">Name</Label>
                      <Input id="su-name" />
                      <div className="grid gap-3">
                      <Label htmlFor="su-email">Username</Label>
                      <Input id="su-email" />
                    </div>
                    </div>
                    <div className="grid gap-3">
                      <Label htmlFor="su-email">Email</Label>
                      <Input id="su-email" />
                    </div>
                    <div className="grid gap-3">
                      <Label htmlFor="su-password">Password</Label>
                      <Input id="su-password" type="password" />
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Button onClick={handleSignup}>Sign up</Button>
                  </CardFooter>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 px-8">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="text-sm text-slate-600">Powered by ExamEngine</div>
          <div className="flex items-center gap-3">
            <Link href="/about" className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm">About</Link>
            <Link href="/faq" className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm">FAQ</Link>
            <Link href="/contact" className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm">Contact us</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
