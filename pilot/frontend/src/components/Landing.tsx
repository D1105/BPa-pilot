import { Car, Shield, Clock, Banknote, ChevronRight, MessageCircle, Globe, Truck, FileCheck } from 'lucide-react'

interface LandingProps {
  onOpenChat: () => void
  onOpenAdmin?: () => void
}

export default function Landing({ onOpenChat, onOpenAdmin }: LandingProps) {
  const features = [
    {
      icon: Globe,
      title: 'Авто из любой страны',
      description: 'Корея, Япония, Германия, США — найдём и привезём любой автомобиль',
    },
    {
      icon: Shield,
      title: 'Полная проверка',
      description: 'История, пробег, ДТП — проверяем каждый автомобиль перед покупкой',
    },
    {
      icon: FileCheck,
      title: 'Растаможка под ключ',
      description: 'Берём на себя все документы и таможенное оформление',
    },
    {
      icon: Truck,
      title: 'Доставка до двери',
      description: 'Логистика морем, ж/д или авто — выберем оптимальный маршрут',
    },
    {
      icon: Banknote,
      title: 'Прозрачные цены',
      description: 'Фиксированная комиссия, никаких скрытых платежей',
    },
    {
      icon: Clock,
      title: 'Сроки 30-60 дней',
      description: 'От заказа до получения ключей — контролируем каждый этап',
    },
  ]

  const stats = [
    { value: '500+', label: 'Автомобилей доставлено' },
    { value: '4.9', label: 'Рейтинг клиентов' },
    { value: '30', label: 'Дней средняя доставка' },
    { value: '0', label: 'Скрытых комиссий' },
  ]

  const popularCars = [
    { name: 'Hyundai Tucson', price: 'от 2.1 млн ₽', image: '🚙' },
    { name: 'Toyota Camry', price: 'от 2.8 млн ₽', image: '🚗' },
    { name: 'BMW X5', price: 'от 4.5 млн ₽', image: '🚘' },
    { name: 'Mercedes GLE', price: 'от 5.2 млн ₽', image: '🚐' },
  ]

  return (
    <div className="relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
      <div className="absolute top-1/2 right-0 w-80 h-80 bg-accent/20 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-primary-400/10 rounded-full blur-3xl" />

      {/* Header */}
      <header className="relative z-10 px-6 py-4">
        <nav className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-accent flex items-center justify-center">
              <Car className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white font-display">АвтоИмпорт</h1>
              <p className="text-xs text-primary-300">Pro</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-300">
            <a href="#features" className="hover:text-white transition-colors">Услуги</a>
            <a href="#popular" className="hover:text-white transition-colors">Популярные авто</a>
            <a href="#process" className="hover:text-white transition-colors">Как это работает</a>
          </div>
          <button
            onClick={onOpenChat}
            className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-dark text-white rounded-full font-medium transition-all hover:scale-105 glow-orange"
          >
            <MessageCircle className="w-4 h-4" />
            <span>Консультация</span>
          </button>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 px-6 py-20 md:py-32">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-primary-300 text-sm mb-6">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              ИИ-консультант онлайн 24/7
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white leading-tight mb-6 font-display">
              Автомобиль мечты{' '}
              <span className="gradient-text">из-за рубежа</span>
            </h1>
            <p className="text-lg md:text-xl text-gray-300 mb-8 leading-relaxed">
              Подберём, проверим, привезём и растаможим автомобиль под ключ. 
              Без посредников, с гарантией и фиксированной ценой.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={onOpenChat}
                className="group flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-accent to-orange-500 hover:from-orange-500 hover:to-accent text-white rounded-2xl font-semibold text-lg transition-all hover:scale-105 glow-orange"
              >
                Подобрать авто
                <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
              <button className="flex items-center justify-center gap-3 px-8 py-4 glass text-white rounded-2xl font-semibold text-lg hover:bg-white/10 transition-all">
                <Clock className="w-5 h-5" />
                Рассчитать стоимость
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="relative z-10 px-6 py-12">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat, i) => (
              <div
                key={i}
                className="glass rounded-2xl p-6 text-center hover:bg-white/10 transition-all"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="text-3xl md:text-4xl font-bold gradient-text font-display mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              Полный цикл услуг
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              От поиска автомобиля до передачи ключей — берём на себя все этапы
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <div
                key={i}
                className="group glass rounded-2xl p-6 hover:bg-white/10 transition-all cursor-pointer"
              >
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-7 h-7 text-primary-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Popular Cars */}
      <section id="popular" className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              Популярные модели
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Самые востребованные автомобили, которые мы привозим
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {popularCars.map((car, i) => (
              <div
                key={i}
                className="group glass rounded-2xl p-6 hover:bg-white/10 transition-all cursor-pointer"
                onClick={onOpenChat}
              >
                <div className="text-6xl mb-4 group-hover:scale-110 transition-transform">
                  {car.image}
                </div>
                <h3 className="text-lg font-semibold text-white mb-1">{car.name}</h3>
                <p className="text-accent font-medium">{car.price}</p>
                <button className="mt-4 w-full py-2 rounded-lg bg-white/5 text-sm text-gray-300 hover:bg-white/10 transition-colors">
                  Узнать подробнее
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Process */}
      <section id="process" className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              Как это работает
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              4 простых шага до вашего нового автомобиля
            </p>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: '01', title: 'Консультация', desc: 'Обсуждаем ваши пожелания и бюджет с ИИ-ассистентом' },
              { step: '02', title: 'Подбор', desc: 'Находим подходящие варианты и проверяем историю' },
              { step: '03', title: 'Покупка', desc: 'Выкупаем авто и оформляем все документы' },
              { step: '04', title: 'Доставка', desc: 'Привозим и передаём вам ключи' },
            ].map((item, i) => (
              <div key={i} className="relative">
                <div className="glass rounded-2xl p-6 h-full">
                  <div className="text-5xl font-bold text-white/10 font-display mb-4">
                    {item.step}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-gray-400 text-sm">{item.desc}</p>
                </div>
                {i < 3 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-0.5 bg-gradient-to-r from-primary-500 to-accent" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <div className="glass rounded-3xl p-8 md:p-12 text-center glow-blue">
            <h2 className="text-2xl md:text-4xl font-bold text-white mb-4 font-display">
              Готовы найти свой автомобиль?
            </h2>
            <p className="text-gray-300 mb-8 max-w-xl mx-auto">
              Наш ИИ-консультант доступен 24/7 и поможет подобрать идеальный вариант под ваш бюджет
            </p>
            <button
              onClick={onOpenChat}
              className="inline-flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-accent to-orange-500 text-white rounded-2xl font-semibold text-lg hover:scale-105 transition-transform glow-orange"
            >
              <MessageCircle className="w-6 h-6" />
              Начать консультацию
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 px-6 py-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-400 to-accent flex items-center justify-center">
              <Car className="w-5 h-5 text-white" />
            </div>
            <span className="text-white font-semibold">АвтоИмпорт Pro</span>
          </div>
          <p className="text-gray-500 text-sm">
            © 2026 АвтоИмпорт Pro. Пилотный проект.{' '}
            <button 
              onClick={onOpenAdmin}
              className="text-gray-600 hover:text-gray-400 transition-colors"
            >
              [Админ]
            </button>
          </p>
        </div>
      </footer>

      {/* Floating Chat Button */}
      <button
        onClick={onOpenChat}
        className="fixed bottom-6 right-6 z-50 w-16 h-16 bg-gradient-to-br from-accent to-orange-500 rounded-full flex items-center justify-center shadow-2xl hover:scale-110 transition-transform glow-orange animate-bounce-slow"
      >
        <MessageCircle className="w-7 h-7 text-white" />
      </button>
    </div>
  )
}
