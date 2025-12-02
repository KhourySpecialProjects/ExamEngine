export const steps: any = [
  {
    tour: "tour1",
    steps: [
      {
        icon: <>👋</>,
        title: "Upload CSV",
        content: <>Click here to upload your CSV files and name your dataset.</>,
        selector: "#upload-id",
        side: "right",
        showControls: true,
        pointerPadding: 0,
        pointerRadius: 11,
      },
      {
        icon: <>🪄</>,
        title: "Generate Schedule",
        content: <>Click here to generate your schedule with parameters wanted</>,
        selector: "#generate-id",
        side: "right",
        showControls: true,
        pointerPadding: 0,
        pointerRadius: 11,
      },
      {
        icon: <>🎉</>,
        title: "Settings",
        content: <>Click here to check account information and for admin role to check 
        which users are approved or who requested an access to use the system</>,
        selector: "#settings-id",
        side: "bottom",
        showControls: true,
        pointerPadding: 0,
        pointerRadius: 11,
      },
      {
        icon: <>🎉</>,
        title: "Notifications",
        content: <>Click here to see the notifications about who wants to share a schedule with you.</>,
        selector: "#notifications-id",
        side: "bottom",
        showControls: true,
        pointerPadding: 0,
        pointerRadius: 11,
      },
    ],
  },
];