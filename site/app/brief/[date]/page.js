import { listData } from "../../lib";
import BriefView from "./view";

export function generateStaticParams() {
  return listData("briefing").map((date) => ({ date }));
}

export default async function Page({ params }) {
  const { date } = await params;
  return <BriefView date={date} />;
}
