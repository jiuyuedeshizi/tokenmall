"use client";

import Image from "next/image";
import Link from "next/link";

export function PlatformBrand({ href }: { href: string }) {
  return (
    <Link className="-ml-2 flex min-w-[284px] items-center gap-0" href={href}>
      <div className="relative h-[36px] w-[114px] overflow-hidden">
        <Image
          alt="忆捷EAGET"
          className="absolute left-[-32px] top-1/2 max-w-none -translate-y-1/2"
          priority
          height={94}
          src="/logo.jpg"
          width={154}
        />
      </div>
      <div className="-ml-3 text-[17px] font-black leading-none tracking-[-0.03em] text-[#172033] md:text-[18px]">
        忆捷开放平台
      </div>
    </Link>
  );
}
