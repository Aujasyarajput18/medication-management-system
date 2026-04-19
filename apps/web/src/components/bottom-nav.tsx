'use client';

/**
 * Aujasya — Bottom Navigation Bar
 * 5-tab navigation with active state, icons, and safe area padding.
 * Touch targets ≥44px per WCAG.
 */

import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: string;
  activeIcon: string;
}

export function BottomNav({ locale }: { locale: string }) {
  const pathname = usePathname();
  const t = useTranslations('nav');

  const items: NavItem[] = [
    {
      href: `/${locale}/today`,
      label: t('today'),
      icon: '🏠',
      activeIcon: '🏠',
    },
    {
      href: `/${locale}/medicines`,
      label: t('medicines'),
      icon: '💊',
      activeIcon: '💊',
    },
    {
      href: `/${locale}/calendar`,
      label: t('calendar'),
      icon: '📅',
      activeIcon: '📅',
    },
    {
      href: `/${locale}/caregiver`,
      label: t('caregiver'),
      icon: '👥',
      activeIcon: '👥',
    },
    {
      href: `/${locale}/settings`,
      label: t('settings'),
      icon: '⚙️',
      activeIcon: '⚙️',
    },
  ];

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card/95 backdrop-blur-lg"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-lg items-center justify-around pb-safe">
        {items.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex min-h-touch min-w-touch flex-col items-center justify-center gap-0.5 px-3 py-2 text-xs transition-colors',
                isActive
                  ? 'text-primary font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="text-xl leading-none" aria-hidden="true">
                {isActive ? item.activeIcon : item.icon}
              </span>
              <span className="leading-tight">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
