import Navbar from "@/app/components/landing/navbar";
import HeroSection from "@/app/components/landing/hero";

export const metadata = {
  title: "MeetNote — Video meetings with transcripts and summaries",
  description:
    "MeetNote is a video meeting platform with live transcription and clear summaries.",
};

const HomePage = () => {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#0f1419] text-slate-100">
      <Navbar />
      <main className="flex flex-1">
        <HeroSection />
      </main>
    </div>
  );
};

export default HomePage;

