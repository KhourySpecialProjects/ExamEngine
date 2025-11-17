import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const heroStats = [
  { label: "Exams scheduled", value: "4,042" },
  { label: "DSATUR runtime", value: "< 2 min" },
  { label: "Hard conflicts", value: "0 recorded" },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <section className="relative isolate overflow-hidden bg-white text-gray-900">
        <div className="mx-auto flex max-w-5xl flex-col items-center px-6 py-20 text-center">
          <div className="mb-6 flex items-center gap-3 text-muted-foreground">
            <Image
              src="/logo.svg"
              alt="ExamEngine logo"
              width={180}
              height={24}
            />
          </div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 py-1 text-xs font-medium uppercase tracking-[0.2em] text-gray-500">
            <Sparkles className="h-3 w-3" />
            Better exam planning starts here
          </div>

          <h1 className="text-3xl font-semibold leading-tight text-gray-900 sm:text-4xl lg:text-5xl">
            ExamEngine turns complex exam planning into fast, 
            conflict-free scheduling.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            Built for Registrar teams and academic departments, ExamEngine automates 
            the hardest parts of final exam scheduling. Upload enrollment data, adjust 
            scheduling constraints, and generate optimized exam timelines in minutes—without 
            the manual conflict checking or endless email threads. Students and instructors 
            get fair, well-balanced schedules, and schools save hours of administrative work.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link href="/signup">
                Create an account
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-gray-200 text-gray-900 hover:bg-gray-50"
            >
              <Link href="/login">Log in</Link>
            </Button>
          </div>

          <div className="mt-10 flex items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Built with secure roles and auditable scheduling history
          </div>

          <div className="mt-12 grid w-full gap-4 rounded-3xl border border-gray-100 bg-gray-50/80 p-6 sm:grid-cols-3">
            {heroStats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-gray-100 bg-white px-4 py-5 text-left"
              >
                <div className="text-3xl font-semibold text-gray-900">
                  {stat.value}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
