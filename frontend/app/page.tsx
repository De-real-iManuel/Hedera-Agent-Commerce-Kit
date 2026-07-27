import { HeroSection } from "@/components/landing/HeroSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { WhyX402Section } from "@/components/landing/WhyX402Section";
import { WhyHederaSection } from "@/components/landing/WhyHederaSection";
import { ArchitectureSection } from "@/components/landing/ArchitectureSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { DemoShowcaseSection } from "@/components/landing/DemoShowcaseSection";
import { OpenSourceSection } from "@/components/landing/OpenSourceSection";

export default function Home() {
  return (
    <>
      <HeroSection />
      <ProblemSection />
      <WhyX402Section />
      <WhyHederaSection />
      <ArchitectureSection />
      <FeaturesSection />
      <DemoShowcaseSection />
      <OpenSourceSection />
    </>
  );
}
