import { listData } from "../../lib";
import ConceptView from "./view";

export function generateStaticParams() {
  return listData("concept").map((key) => ({ key }));
}

export default async function Page({ params }) {
  const { key } = await params;
  return <ConceptView file={key} />;
}
