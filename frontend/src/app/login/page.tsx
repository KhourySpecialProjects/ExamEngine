"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/lib/store/authStore";
import Image from "next/image";

export default function Login() {
  const login = useAuthStore((state) => state.login);
  const signup = useAuthStore((state) => state.signup);
  const router = useRouter();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [suName, setSuName] = React.useState("");
  const [suEmail, setSuEmail] = React.useState("");
  const [suPassword, setSuPassword] = React.useState("");

  const handleLogin = async () => {
    try {
      await login(email, password);
      toast.success("Logged In");
      router.push("/dashboard");
    } catch (_error) {
      toast.error("Login Failed");
    }
  };

  const handleSignup = async () => {
    if (!suEmail || !suPassword) {
      toast.error("Please fill name, email and password to sign up.");
      return;
    }
    if (!suEmail.includes("@")) {
      toast.error("Please enter a valid email address.");
      return;
    }

    try {
      await signup(suName, suEmail, suPassword);
      toast.success("Sign Up Successful");
      router.push("/dashboard");
    } catch (err: unknown) {
      try {
        const errorMessage = err instanceof Error ? err.message : String(err);
        const parsed = JSON.parse(errorMessage);
        toast.error(
          `Signup failed: ${parsed.detail || JSON.stringify(parsed)}`,
        );
      } catch (_err: unknown) {
        toast.error("Signup failed");
      }
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-3">
          <Image
            src="/logo.svg"
            alt="icon"
            width={300}
            height={300}
            className="py-8 px-10"
          />
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
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                      />
                    </div>

                    <div className="grid gap-3">
                      <Label htmlFor="password">Password</Label>
                      <Input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
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
                      <Input
                        id="su-name"
                        value={suName}
                        onChange={(e) => setSuName(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-3">
                      <Label htmlFor="su-email">Email</Label>
                      <Input
                        id="su-email"
                        value={suEmail}
                        onChange={(e) => setSuEmail(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-3">
                      <Label htmlFor="su-password">Password</Label>
                      <Input
                        id="su-password"
                        type="password"
                        value={suPassword}
                        onChange={(e) => setSuPassword(e.target.value)}
                      />
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
            <Link
              href="/about"
              className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm"
            >
              About
            </Link>
            <Link
              href="/faq"
              className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm"
            >
              FAQ
            </Link>
            <Link
              href="/contact"
              className="px-3 py-1 rounded-full bg-slate-900 text-white text-sm"
            >
              Contact us
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
