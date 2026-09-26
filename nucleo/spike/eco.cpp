// Lê uma instância em texto pela entrada padrão e devolve a soma dos ganhos:
// mede o custo de passar a instância da API ao núcleo por processo.
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <vector>
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    long long n, a;
    std::cin >> n >> a;
    std::vector<long long> custo(a);
    for (auto &c : custo) std::cin >> c;
    long long soma = 0, g;
    for (long long i = 0; i < n * a; ++i) { std::cin >> g; soma += g; }
    std::printf("%lld %lld\n", n, soma);
    return 0;
}
