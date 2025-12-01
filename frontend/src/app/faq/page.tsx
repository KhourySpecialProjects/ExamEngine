import Link from "next/link";

const faqs = [
  {
    question: "What files do I need to upload?",
    answer:
      "You need three CSVs: courses (CRN, course_ref, num_students), enrollment (student_id, CRN, instructor_name), and classrooms (room_name, capacity). Upload them under Datasets in the dashboard.",
  },
  {
    question: "How are conflicts handled?",
    answer:
      "The DSATUR engine models student overlaps, instructor overlaps, and room capacity. It also respects max exams per student per day and back-to-back avoidance when those options are set.",
  },
  {
    question: "How long does generation take?",
    answer:
      "Most schedules generate in under two minutes. Larger datasets may take longer, but you can rerun with tweaked parameters without re-uploading data.",
  },
  {
    question: "Can I share a schedule with teammates?",
    answer:
      "Yes. Open a schedule from the dashboard and use Share to give view or edit access. Shared schedules keep the same parameters and conflict summaries.",
  },
  {
    question: "What if conflicts remain?",
    answer:
      "Conflicts are surfaced in the density and list views. You can adjust parameters, room assignments, or regenerate. We never silently drop exams.",
  },
  {
    question: "Where do I see what changed?",
    answer:
      "Each run keeps its parameters and conflict breakdown. Re-running with new settings creates a new schedule so you can compare outcomes.",
  },
];

export default function FaqPage() {
  return (
    <div className="min-h-screen bg-white px-6 py-16 text-slate-900">
      <div className="mx-auto flex max-w-4xl flex-col gap-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
            FAQ
          </p>
          <h1 className="text-3xl font-semibold">Frequently asked questions</h1>
          <p className="max-w-2xl text-slate-600">
            Quick answers to common questions about uploading datasets,
            generating schedules, handling conflicts, and sharing results with
            your team.
          </p>
        </header>

        <section className="grid gap-4">
          {faqs.map((item) => (
            <article
              key={item.question}
              className="rounded-xl border border-slate-200 bg-slate-50/60 p-5 shadow-sm"
            >
              <h2 className="text-lg font-semibold text-slate-900">
                {item.question}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {item.answer}
              </p>
            </article>
          ))}
        </section>

        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm text-slate-500">
              Powered by ExamEngine
            </span>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/login#signup"
                className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                Sign up
              </Link>
              <Link
                href="/login"
                className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-200"
              >
                Login
              </Link>
              <Link
                href="/about"
                className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-200"
              >
                About
              </Link>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
