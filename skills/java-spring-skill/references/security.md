# Spring Security 6 — JWT, Method Security, OAuth2

## Security Filter Chain

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.ignoringRequestMatchers("/api/auth/**")) // API stateless JWT thường tắt CSRF cho endpoint auth; nếu có session-based endpoint khác, giữ CSRF bật cho endpoint đó
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**", "/actuator/health").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of("http://localhost:3000"));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }
}
```

## JWT Filter + Service

```java
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }
        String jwt = authHeader.substring(7);
        try {
            String username = jwtService.extractUsername(jwt);
            if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
                UserDetails userDetails = userDetailsService.loadUserByUsername(username);
                if (jwtService.isTokenValid(jwt, userDetails)) {
                    var authToken = new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
                    authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                }
            }
        } catch (JwtException e) {
            log.error("JWT validation failed", e);
        }
        chain.doFilter(request, response);
    }
}

@Service
public class JwtService {
    @Value("${jwt.secret}") private String secretKey;
    @Value("${jwt.expiration}") private long jwtExpiration;

    public String extractUsername(String token) { return extractClaim(token, Claims::getSubject); }

    public <T> T extractClaim(String token, Function<Claims, T> resolver) {
        return resolver.apply(extractAllClaims(token));
    }

    public String generateToken(UserDetails userDetails) {
        return Jwts.builder()
            .setSubject(userDetails.getUsername())
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + jwtExpiration))
            .signWith(getSignInKey(), SignatureAlgorithm.HS256)
            .compact();
    }

    public boolean isTokenValid(String token, UserDetails userDetails) {
        return extractUsername(token).equals(userDetails.getUsername())
            && extractClaim(token, Claims::getExpiration).after(new Date());
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parserBuilder().setSigningKey(getSignInKey()).build().parseClaimsJws(token).getBody();
    }

    private Key getSignInKey() { return Keys.hmacShaKeyFor(Decoders.BASE64.decode(secretKey)); }
}
```

`jwt.secret` PHẢI đọc từ biến môi trường/secret manager (`${JWT_SECRET}`), không hardcode trong `application.yml` — rủi ro bảo mật nếu file config bị commit.

## UserDetailsService + Authentication Service

```java
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {
    private final UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) {
        return userRepository.findByEmailWithRoles(email)
            .map(user -> org.springframework.security.core.userdetails.User.builder()
                .username(user.getEmail())
                .password(user.getPassword())
                .authorities(user.getRoles().stream().map(r -> new SimpleGrantedAuthority("ROLE_" + r.getName())).toList())
                .disabled(!user.getActive())
                .build())
            .orElseThrow(() -> new UsernameNotFoundException("User not found: " + email));
    }
}

@Service
@RequiredArgsConstructor
@Transactional
public class AuthenticationService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    public AuthenticationResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new DuplicateResourceException("Email already registered");
        }
        User user = userRepository.save(User.builder()
            .email(request.email())
            .password(passwordEncoder.encode(request.password()))
            .roles(Set.of(Role.builder().name("USER").build()))
            .active(true)
            .build());
        return new AuthenticationResponse(jwtService.generateToken(toUserDetails(user)));
    }

    public AuthenticationResponse login(LoginRequest request) {
        authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(request.email(), request.password()));
        User user = userRepository.findByEmail(request.email()).orElseThrow();
        return new AuthenticationResponse(jwtService.generateToken(toUserDetails(user)));
    }

    private UserDetails toUserDetails(User user) {
        return org.springframework.security.core.userdetails.User.builder()
            .username(user.getEmail()).password(user.getPassword())
            .authorities(user.getRoles().stream().map(r -> new SimpleGrantedAuthority("ROLE_" + r.getName())).toList())
            .build();
    }
}
```

## Method-Level Security

```java
@Service
@RequiredArgsConstructor
public class UserService {
    @PreAuthorize("hasRole('ADMIN')")
    public List<User> getAllUsers() { return userRepository.findAll(); }

    @PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
    public User getUserById(Long userId) {
        return userRepository.findById(userId).orElseThrow(() -> new ResourceNotFoundException("User not found"));
    }

    @PostAuthorize("returnObject.email == authentication.principal.username or hasRole('ADMIN')")
    public User findUserByEmail(String email) {
        return userRepository.findByEmail(email).orElseThrow();
    }
}
```

`@PreAuthorize` check TRƯỚC khi method chạy (dùng khi biết điều kiện từ tham số đầu vào); `@PostAuthorize` check SAU khi có kết quả trả về (dùng khi điều kiện phụ thuộc chính object trả về, VD chỉ xem được record của chính mình).

## OAuth2 Resource Server (JWT do IdP ngoài phát hành — VD Keycloak/Auth0/Cognito)

Dùng khi project KHÔNG tự phát hành JWT (khác với JwtService ở trên) mà validate token do 1 Identity Provider ngoài cấp.

```java
@Configuration
@EnableWebSecurity
public class OAuth2ResourceServerConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())));
        return http.build();
    }

    @Bean
    public JwtDecoder jwtDecoder() { return JwtDecoders.fromIssuerLocation("https://auth.example.com"); }

    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        var grantedAuthoritiesConverter = new JwtGrantedAuthoritiesConverter();
        grantedAuthoritiesConverter.setAuthoritiesClaimName("roles");
        grantedAuthoritiesConverter.setAuthorityPrefix("ROLE_");
        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(grantedAuthoritiesConverter);
        return converter;
    }
}
```

## Security Utility (đọc user hiện tại ngoài `@AuthenticationPrincipal`)

```java
@Component("userSecurityService")
public class UserSecurityService {
    public String getCurrentUsername() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        return (auth != null && auth.getPrincipal() instanceof UserDetails ud) ? ud.getUsername() : null;
    }
}
```

## Quick Reference

| Annotation | Purpose |
|-----------|---------|
| `@EnableWebSecurity` / `@EnableMethodSecurity` | Bật security tầng HTTP / method |
| `@PreAuthorize` / `@PostAuthorize` | Check quyền trước/sau khi method chạy |
| `@Secured` / `@RolesAllowed` | Role-based (kiểu cũ hơn `@PreAuthorize`) |
| `SecurityContextHolder` | Truy cập security context hiện tại |
| `@AuthenticationPrincipal` | Inject user hiện tại vào controller method |

## Security Best Practices

- HTTPS bắt buộc ở production, không chỉ ở local.
- Secret (JWT signing key, DB password) LUÔN qua biến môi trường/secret manager, không hardcode.
- `BCryptPasswordEncoder` strength tối thiểu 12.
- Có cơ chế refresh token thay vì access token sống quá lâu.
- Rate-limit riêng cho endpoint auth (login/register) — mục tiêu phổ biến của brute-force.
- Không log giá trị JWT/password ra log thường.
