import { Link, Sparkles } from "lucide-react";
import Image from "next/image";

export default function NotFound() {
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
            Sorry! The page you are looking for does not exist.
          </div>

          <Link
            href="/contact"
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Go back to the Dashboard.
          </Link>
        </div>
      </section>
    </div>
  );
}
