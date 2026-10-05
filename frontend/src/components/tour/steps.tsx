export const steps = [
  {
    tour: "tour1",
    steps: [
      {
        icon: <>👋</>,
        title: "Control Center",
        content: (
          <>
            The Control Center is your main workspace. From here, you can manage
            datasets, upload new files, and generate exam schedules. This is
            where most of your actions begin.
          </>
        ),
        selector: "#control-center",
        side: "right" as const,
        showControls: true,
        pointerPadding: 5,
        pointerRadius: 11,
      },
      {
        icon: <>📤</>,
        title: "Upload CSV",
        content: (
          <>
            Upload your CSV files here. Name the dataset, add the courses,
            enrollments and rooms files (plus any optional ones), and it becomes
            available for generating schedules.
          </>
        ),
        selector: "#upload-id",
        side: "right" as const,
        showControls: true,
        pointerPadding: 5,
        pointerRadius: 11,
      },
      {
        icon: <>🪄</>,
        title: "Generate Schedule",
        content: (
          <>
            Once your dataset is ready, come here to generate a new schedule.
            Choose the parameters you want, and the system will automatically
            create an optimized exam schedule for you.
          </>
        ),
        selector: "#generate-id",
        side: "right" as const,
        showControls: true,
        pointerPadding: 5,
        pointerRadius: 11,
      },
      {
        icon: <>📅</>,
        title: "Schedule Dashboard",
        content: (
          <>
            This page lists all your schedules. Switch between List and By
            dataset, sort and page through them, and open one to view, validate,
            share or export it.
          </>
        ),
        selector: "#schedule-view",
        side: "bottom" as const,
        showControls: true,
        pointerPadding: 5,
        pointerRadius: 11,
      },
      {
        icon: <>⚙</>,
        title: "Settings & Users",
        content: (
          <>
            Access your account information here. If you're an admin, you can
            also review user requests, approve new accounts, and manage existing
            user permissions.
          </>
        ),
        selector: "#settings-id",
        side: "bottom" as const,
        showControls: true,
        pointerPadding: 5,
        pointerRadius: 11,
      },
    ],
  },
];
