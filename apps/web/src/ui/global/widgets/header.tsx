import { Link } from '@tanstack/react-router'
import { Badge } from '@/ui/shadcn/components/badge'
import { Award, BookOpen, Compass, Terminal } from 'lucide-react'

export function Header() {
  return (
    <header className='sticky top-0 z-40 w-full border-b border-divider bg-page/95 backdrop-blur'>
      <div className='mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6'>
        <div className='flex items-center gap-6'>
          <Link to='/' className='flex items-center gap-2 group'>
            <span className='flex h-8 w-8 items-center justify-center rounded-[2px] bg-selo-fill text-white font-bold text-lg leading-none'>
              師
            </span>
            <div className='flex flex-col'>
              <span className='font-display text-xl font-bold tracking-[0.1em] uppercase text-text-primary group-hover:text-white transition-colors'>
                SHIFU
              </span>
            </div>
          </Link>

          <nav className='hidden md:flex items-center gap-4 text-xs uppercase tracking-wider font-display'>
            <Link
              to='/'
              className='flex items-center gap-1.5 text-text-secondary hover:text-white transition-colors py-1 px-2 rounded-[2px]'
            >
              <Compass className='size-3.5 text-jade-solid' />
              Objetivos
            </Link>
            <span className='flex items-center gap-1.5 text-text-muted hover:text-white transition-colors py-1 px-2 rounded-[2px]'>
              <BookOpen className='size-3.5 text-jade-solid' />
              Trilha
            </span>
            <span className='flex items-center gap-1.5 text-text-muted hover:text-white transition-colors py-1 px-2 rounded-[2px]'>
              <Award className='size-3.5 text-latao-solid' />
              Conquistas
            </span>
            <span className='flex items-center gap-1.5 text-text-muted hover:text-white transition-colors py-1 px-2 rounded-[2px]'>
              <Terminal className='size-3.5 text-selo-text' />
              Prática
            </span>
          </nav>
        </div>

        <div className='flex items-center gap-3'>
          <Badge variant='latao' className='gap-1'>
            <span>🔥</span>
            <span>3 dias</span>
          </Badge>
          <Badge variant='latao' className='gap-1'>
            <span>⚡</span>
            <span>120 XP</span>
          </Badge>
          <Badge variant='jade' className='gap-1'>
            <span>●</span>
            <span>Lógica I</span>
          </Badge>
        </div>
      </div>
    </header>
  )
}
