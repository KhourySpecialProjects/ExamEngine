"use client";

import Link from "next/link";
import { useState } from "react";

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
  {
    question: "What columns are required in each CSV?",
    answer:
      "Courses: CRN, course_ref, num_students. Enrollment: student_id, CRN, instructor_name. Classrooms: room_name, capacity. Stick to these headers so validation passes.",
  },
  {
    question: "Can I reuse datasets across runs?",
    answer:
      "Yes. Once uploaded, datasets stay in Datasets. You can generate multiple schedules from the same uploads without re-uploading files.",
  },
  {
    question: "How do I adjust constraints?",
    answer:
      "In the scheduler panel, adjust max exams per student per day, toggle back-to-back avoidance, set max days, and prioritize large courses before running.",
  },
  {
    question: "Can I export results?",
    answer:
      "Yes. Export CSVs from the schedule views. Shared users see the same schedule data you export.",
  },
  {
    question: "Why might a run fail?",
    answer:
      "Common causes: missing required columns, malformed CSV headers, or no rooms with enough capacity. Check the conflict/summary and try again after fixing the input.",
  },
  {
    question: "How do I interpret the conflict breakdown?",
    answer:
      "Use the density and list views: they show which CRNs, students, or instructors are involved so you can tweak parameters or room assignments.",
  },
  {
    question: "Do I need to restart after changing parameters?",
    answer:
      "No. Adjust parameters and run again—each run is stored separately so you can compare outputs.",
  },
  {
    question: "How do I remove a dataset?",
    answer:
      "Open Datasets in the dashboard and delete the upload. This removes the dataset but existing schedules that used it remain for reference.",
  },
];

export default function FaqPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (idx: number) => {
    setOpenIndex((current) => (current === idx ? null : idx));
  };

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
          {faqs.map((item, idx) => {
            const isOpen = openIndex === idx;
            return (
              <article
                key={item.question}
                className="rounded-xl border border-slate-200 bg-slate-50/60 shadow-sm"
              >
                <button
                  type="button"
                  onClick={() => toggle(idx)}
                  className="flex w-full items-center justify-between gap-3 p-5 text-left"
                  aria-expanded={isOpen}
                >
                  <h2 className="text-lg font-semibold text-slate-900">
                    {item.question}
                  </h2>
                  <span className="text-sm text-slate-500">
                    {isOpen ? "−" : "+"}
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-slate-200 px-5 pb-4 pt-3">
                    <p className="text-sm leading-relaxed text-slate-700">
                      {item.answer}
                    </p>
                  </div>
                )}
              </article>
            );
          })}
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
