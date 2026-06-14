"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getCredits } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Console" },
  { href: "/builder", label: "Builder" },
  { href: "/impact", label: "Impact" },
];

export default function Nav() {
  const pathname = usePathname();
  const [credits, setCredits] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    getCredits()
      .then((c) => alive && setCredits(c.credits))
      .catch(() => alive && setCredits(null));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <nav className="nav">
      <span className="brand">FlowForge</span>
      {LINKS.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={pathname === l.href ? "active" : undefined}
        >
          {l.label}
        </Link>
      ))}
      <span className="spacer" />
      {credits !== null && (
        <span className="credits">
          Credits: <b>{credits}</b>
        </span>
      )}
    </nav>
  );
}
