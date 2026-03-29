"use client";

import Image from "next/image";
import Link from "next/link";

export function PlatformBrand({ href }: { href: string }) {
  return (
    <Link className="flex min-w-[248px] items-start gap-0.5" href={href}>
      <div className="flex flex-col items-start leading-none">
        <Image alt="EAGET" className="h-auto w-[82px]" height={42} priority src="/eaget-logo.svg" width={82} />
        <div className="mt-0.5 pl-[1px] text-[10px] italic leading-none text-[#9aa4b2]">Easy to Get</div>
      </div>
      <div className="pt-0.5 text-[17px] font-black tracking-[-0.03em] text-[#172033] md:text-[18px]">亿捷开放平台</div>
    </Link>
  );
}
