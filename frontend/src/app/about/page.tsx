import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  Database,
  LineChart,
  Medal,
  ShieldCheck,
  Smile,
  Sparkles,
  Timer,
  Users,
  Workflow,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const heroStats = [
  { label: "Exams scheduled", value: "4,042" },
  { label: "DSATUR runtime", value: "< 2 min" },
  { label: "Hard conflicts", value: "0 recorded" },
];

const capabilityCards = [
  {
    title: "See conflicts clearly",
    description:
      "Every generated schedule includes a conflict breakdown so teams can review issues before sharing with students.",
    icon: ShieldCheck,
    bullets: ["Conflict summaries", "Cell-level breakdowns"],
  },
  {
    title: "Reduce manual work",
    description:
      "Upload course, enrollment, and room data once, reuse datasets, and let DSATUR handle the heavy lifting.",
    icon: ClipboardCheck,
    bullets: ["Reusable datasets", "Room & course mapping"],
  },
  {
    title: "Lower planner stress",
    description:
      "Fast runs, clear visualizations, and saved presets mean your team spends time deciding—not troubleshooting.",
    icon: Smile,
    bullets: ["Parameter presets stay saved", "Live generation status"],
  },
  {
    title: "Improve outcomes",
    description:
      "Balance large exams, avoid back-to-back conflicts, and publish confident schedules students can follow.",
    icon: Medal,
    bullets: ["Prioritize high-impact exams", "Back-to-back controls"],
  },
  {
    title: "Shared visibility",
    description:
      "Schedules live behind a secure login so registrar teammates can open the same source of truth.",
    icon: Users,
    bullets: ["Team access", "Consistent records"],
  },
  {
    title: "Visual insight",
    description:
      "Calendar, density, list, and statistics views highlight conflicts, load, and room pressure without leaving ExamEngine.",
    icon: LineChart,
    bullets: ["Calendar & list modes", "Department filters"],
  },
];

const workflowSteps = [
  {
    title: "Upload & validate",
    description:
      "Drag in enrollment, room, and instructor files. We flag issues instantly so you start with clean data.",
    icon: Sparkles,
  },
  {
    title: "Optimize with DSATUR",
    description:
      "Adjust parameters, run the generator, and review conflicts in under two minutes, no macros or scripts required.",
    icon: Timer,
  },
  {
    title: "Publish & monitor",
    description:
      "Share schedules, export CSVs, and keep an audit trail so late changes and approvals stay organized.",
    icon: CheckCircle2,
  },
];

const foundationHighlights = [
  {
    title: "Data foundation",
    description:
      "Courses, enrollments, and rooms stay attached to each dataset so teams can reuse uploads without rebuilding spreadsheets.",
    icon: Database,
    details: ["Upload CSV exports once", "Datasets scoped to each user"],
  },
  {
    title: "Algorithmic engine",
    description:
      "Graph coloring (DSATUR) models student overlap and room capacity, with adjustable caps for students and instructors.",
    icon: Workflow,
    details: [
      "Runs complete in under two minutes",
      "Controls for max exams per day & back-to-back avoidance",
    ],
  },
  {
    title: "Visualization layer",
    description:
      "Density, compact calendar, detailed list, and statistics views surface key insights without spreadsheet pivots.",
    icon: LineChart,
    details: ["Department filters", "CSV export option"],
  },
  {
    title: "Shared workspace",
    description:
      "Login system lets registrar staff access their generated schedules anywhere and export results that match campus workflows.",
    icon: Users,
    details: ["Schedules stored per user", "CSV export plus in-app views"],
  },
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
            ExamEngine turns complex exam planning into fast, conflict-free
            scheduling.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
            Built for Registrar teams and academic departments, ExamEngine
            automates the hardest parts of final exam scheduling. Upload
            enrollment data, adjust scheduling constraints, and generate
            optimized exam timelines in minutes—without the manual conflict
            checking or endless email threads. Students and instructors get
            fair, well-balanced exam schedules, and schools save hours of
            administrative work.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link href="/login#signup">
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

      <section className="border-t border-gray-100 bg-white">
        <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-600">
              Why ExamEngine
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-gray-900">
              Built for registrar leaders, schedulers, and ops partners
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Replace brittle spreadsheets with a platform that was designed for
              complex academic logistics and fast approvals.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {capabilityCards.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.title}
                  className="flex flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50/70 p-6 shadow-sm"
                >
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-gray-900 shadow">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {card.title}
                    </h3>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {card.description}
                    </p>
                  </div>
                  <ul className="space-y-1 text-sm text-gray-800">
                    {card.bullets.map((bullet) => (
                      <li key={bullet} className="flex items-center gap-2">
                        <ArrowUpRight className="h-4 w-4 text-emerald-600" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-white">
        <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-600">
              Platform foundation
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-gray-900">
              What powers ExamEngine behind the scenes
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Data imports, DSATUR scheduling, visualizations, and exports work
              together so teams can trust every run.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {foundationHighlights.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="flex flex-col gap-4 rounded-3xl border border-gray-100 bg-white p-6 shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-50 text-gray-900">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {item.title}
                    </h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.description}
                  </p>
                  <ul className="space-y-1 text-sm text-gray-800">
                    {item.details.map((detail) => (
                      <li key={detail} className="flex items-center gap-2">
                        <ArrowUpRight className="h-4 w-4 text-emerald-600" />
                        {detail}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-slate-900 text-white">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">
              Workflow
            </p>
            <h2 className="mt-2 text-3xl font-semibold">
              A transparent process from intake to publish
            </h2>
            <p className="mt-4 text-lg text-white/80">
              Every stage is documented so stakeholders know who changed what,
              when, and why.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {workflowSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.title}
                  className="relative rounded-3xl border border-white/10 bg-white/5 p-6"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-300">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-sm font-semibold text-white/70">
                      Step {index + 1}
                    </span>
                  </div>
                  <h3 className="mt-4 text-xl font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm text-white/80">
                    {step.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-t border-gray-100 bg-white">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-600">
              So what?
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-gray-900">
              Every feature ties back to shared data, faster approvals, and
              export-ready schedules.
            </h2>
            <div className="mt-5 space-y-4 text-base text-muted-foreground">
              <p>
                The login system means Registrar teammates can share one secure
                workspace, pick up where someone left off, and keep data synced
                without re-uploading files. Combined with per-user storage, each
                dataset and generated schedule stays accessible when leadership
                needs an audit trail.
              </p>
              <p>
                Once a run finishes, teams can export CSVs or rely on our visual
                dashboards to answer questions in minutes. Conflicts, room
                pressure, and departmental allocation are visible at a glance,
                so stakeholders see why a decision was made.
              </p>
              <p>
                Ultimately, ExamEngine helps registrar operations move faster
                with less stress—because the context, data, and outputs live in
                one place built for their workflow.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-gray-100 bg-white">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-600">
            Ready to modernize exam planning?
          </p>
          <h2 className="mt-3 text-3xl font-semibold text-gray-900">
            Start with your datasets. Generate conflict-free schedules this
            term.
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Invite your planning team, upload last term’s CSVs, and see how fast
            ExamEngine surfaces insights you can act on.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link href="/dashboard">
                Go to dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-gray-200 text-gray-900 hover:bg-gray-50"
            >
              <Link href="/login#signup">Create an account</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
