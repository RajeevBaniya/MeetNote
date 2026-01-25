import "./globals.css";

export const metadata = {
  title: "MeetNote",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
