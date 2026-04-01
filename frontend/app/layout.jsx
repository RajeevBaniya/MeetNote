import "./globals.css";
import AuthProvider from "@/app/providers/auth-provider";
import ToastProvider from "@/app/providers/toast-provider";

export const metadata = {
  title: "MeetNote",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

const RootLayout = ({ children }) => {
  return (
    <html lang="en">
      <body className="antialiased">
        <AuthProvider>
          <ToastProvider>{children}</ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
};

export default RootLayout;
