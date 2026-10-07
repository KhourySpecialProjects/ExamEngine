import { useMemo } from "react";
import {
  buildExamGroups,
  type ExamGroups,
} from "@/components/exam-week/examGroups";
import { useCommonExams } from "./useCommonExams";
import { useCourseMerges } from "./useCourseMerges";

/**
 * The dataset's combined and common exams by CRN (owner or anyone a schedule
 * of it is shared with). Empty while loading, without a dataset, or on error.
 */
export function useExamGroups(
  datasetId: string | null | undefined,
): ExamGroups {
  const { merges } = useCourseMerges(datasetId);
  const { commonGroups } = useCommonExams(datasetId, merges);
  return useMemo(
    () => buildExamGroups(merges, commonGroups),
    [merges, commonGroups],
  );
}
