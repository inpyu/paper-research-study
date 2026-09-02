import { readData } from "../../../lib";
import QuizView from "./view";

export function generateStaticParams() {
  const cat = readData("catalog.json") || { tracks: [] };
  return cat.tracks.flatMap((t) => t.courses)
    .filter((c) => c.has_quiz)
    .map((c) => ({ course: c.id }));
}

export default async function Page({ params }) {
  const { course } = await params;
  return <QuizView id={course} />;
}
