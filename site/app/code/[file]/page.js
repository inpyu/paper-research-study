import { listData } from "../../lib";
import FileView from "./view";

export function generateStaticParams() {
  return listData("code").map((file) => ({ file }));
}

export default async function Page({ params }) {
  const { file } = await params;
  return <FileView file={file} />;
}
