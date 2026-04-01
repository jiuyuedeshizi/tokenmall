"use client";

import Image from "next/image";
import Link from "next/link";

export function PlatformBrand({ href }: { href: string }) {
  return (
    <Link className="flex min-w-[284px] items-start" href={href}>
      <div className="flex flex-col items-start leading-none">
        <div className="relative h-[28px] w-[112px] overflow-hidden">
          <Image
            alt="EAGET"
            className="absolute left-[-34px] top-1/2 max-w-none -translate-y-1/2"
            priority
            height={86}
            src="/logo.jpg"
            width={140}
          />
        </div>
        <div className="-mt-1 pl-[1px] text-[10px] italic leading-none text-[#9aa4b2]">Easy to Get</div>
      </div>
      <div className="-ml-[28px] pt-0.5 text-[17px] font-black tracking-[-0.03em] text-[#172033] md:text-[18px]">
        亿捷开放平台
      </div>
    </Link>
  );
}
