import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

// 👇 live backend op Render
const apiBase = 'https://turkish-diaspora-app.onrender.com';

void main() {
  runApp(const DiasporaApp());
}

class DiasporaApp extends StatelessWidget {
  const DiasporaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Turkish Diaspora App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.red,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      home: const HomePage(),
    );
  }
}

// Models
class NewsItem {
  final int id;
  final String title;
  final String sourceName;
  final DateTime publishedAt;
  final String lang;
  final String url;
  final String? summaryNl;
  final String? summaryTr;
  final List<String> tags;
  final List<String> regions;
  final Map<String, dynamic> reactions;

  NewsItem({
    required this.id,
    required this.title,
    required this.sourceName,
    required this.publishedAt,
    required this.lang,
    required this.url,
    this.summaryNl,
    this.summaryTr,
    required this.tags,
    required this.regions,
    required this.reactions,
  });

  factory NewsItem.fromJson(Map<String, dynamic> json) {
    return NewsItem(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      sourceName: json['source_name'] ?? 'News',
      publishedAt: DateTime.tryParse(json['published_at'] ?? '') ?? DateTime.now(),
      lang: json['lang'] ?? 'unknown',
      url: json['url'] ?? '',
      summaryNl: json['summary_nl'],
      summaryTr: json['summary_tr'],
      tags: List<String>.from(json['tags'] ?? []),
      regions: List<String>.from(json['regions'] ?? []),
      reactions: Map<String, dynamic>.from(json['reactions'] ?? {}),
    );
  }

  String get displaySummary => summaryNl ?? summaryTr ?? '';
}

class PagedResponse {
  final List<NewsItem> items;
  final int count;

  PagedResponse({
    required this.items,
    required this.count,
  });

  factory PagedResponse.fromJson(Map<String, dynamic> json) {
    return PagedResponse(
      items: (json['items'] as List)
          .map((item) => NewsItem.fromJson(item))
          .toList(),
      count: json['count'] ?? 0,
    );
  }
}

// API Service
class NewsService {
  static Future<PagedResponse> fetchNews({
    String? lang,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, String>{
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      
      if (lang != null && lang != 'all') {
        queryParams['lang'] = lang;
      }

      final uri = Uri.parse('$apiBase/v1/news').replace(queryParameters: queryParams);
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return PagedResponse.fromJson(data);
      } else {
        throw Exception('Failed to load news: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  static Future<Map<String, int>> toggleReaction(int itemId, String emoji) async {
    try {
      final response = await http.post(
        Uri.parse('$apiBase/v1/reactions'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'item_id': itemId,
          'emoji': emoji,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return Map<String, int>.from(data['reactions'] ?? {});
      } else {
        throw Exception('Failed to toggle reaction');
      }
    } catch (e) {
      throw Exception('Error toggling reaction: $e');
    }
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;
  
  final List<Widget> _pages = [
    const FeedPage(),
    const NewsPage(),
    const Center(child: Text('Music - Coming Soon')),
    const Center(child: Text('Sports - Coming Soon')),
    const Center(child: Text('Events - Coming Soon')),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Turkish Diaspora App'),
      ),
      body: _pages[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (int index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home),
            label: 'For You',
          ),
          NavigationDestination(
            icon: Icon(Icons.newspaper),
            label: 'News',
          ),
          NavigationDestination(
            icon: Icon(Icons.music_note),
            label: 'Music',
          ),
          NavigationDestination(
            icon: Icon(Icons.sports_soccer),
            label: 'Sports',
          ),
          NavigationDestination(
            icon: Icon(Icons.event),
            label: 'Events',
          ),
        ],
      ),
    );
  }
}

class FeedPage extends StatefulWidget {
  const FeedPage({super.key});

  @override
  State<FeedPage> createState() => _FeedPageState();
}

class _FeedPageState extends State<FeedPage> {
  List<NewsItem> items = [];
  bool isLoading = false;
  bool isLoadingMore = false;
  String? selectedLang;
  int limit = 20;
  int offset = 0;
  bool hasMoreItems = true;
  String? error;

  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadNews();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= 
        _scrollController.position.maxScrollExtent - 200) {
      _loadMoreNews();
    }
  }

  Future<void> _loadNews({bool refresh = false}) async {
    if (isLoading) return;

    setState(() {
      isLoading = true;
      error = null;
      if (refresh) {
        offset = 0;
        hasMoreItems = true;
      }
    });

    try {
      final response = await NewsService.fetchNews(
        lang: selectedLang,
        limit: limit,
        offset: offset,
      );

      setState(() {
        if (refresh) {
          items = response.items;
        } else {
          items.addAll(response.items);
        }
        hasMoreItems = response.items.length == limit;
        offset += response.items.length;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _loadMoreNews() async {
    if (isLoadingMore || !hasMoreItems) return;

    setState(() {
      isLoadingMore = true;
    });

    try {
      final response = await NewsService.fetchNews(
        lang: selectedLang,
        limit: limit,
        offset: offset,
      );

      setState(() {
        items.addAll(response.items);
        hasMoreItems = response.items.length == limit;
        offset += response.items.length;
        isLoadingMore = false;
      });
    } catch (e) {
      setState(() {
        isLoadingMore = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load more: $e')),
        );
      }
    }
  }

  void _onLanguageChanged(String? lang) {
    setState(() {
      selectedLang = lang;
      offset = 0;
    });
    _loadNews(refresh: true);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Language Filter Chips - TDA-15
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Text('Filter: ', style: TextStyle(fontWeight: FontWeight.w500)),
              const SizedBox(width: 8),
              FilterChip(
                label: const Text('All'),
                selected: selectedLang == null,
                onSelected: (selected) => _onLanguageChanged(null),
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('🇳🇱'),
                    SizedBox(width: 4),
                    Text('NL'),
                  ],
                ),
                selected: selectedLang == 'nl',
                onSelected: (selected) => _onLanguageChanged(selected ? 'nl' : null),
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('🇹🇷'),
                    SizedBox(width: 4),
                    Text('TR'),
                  ],
                ),
                selected: selectedLang == 'tr',
                onSelected: (selected) => _onLanguageChanged(selected ? 'tr' : null),
              ),
            ],
          ),
        ),
        // News List - TDA-14, TDA-16
        Expanded(
          child: _buildContent(),
        ),
      ],
    );
  }

  Widget _buildContent() {
    if (isLoading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null && items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text('Failed to load news', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _loadNews(refresh: true),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (items.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.article_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('Nog geen nieuws', style: TextStyle(fontSize: 18)),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _loadNews(refresh: true),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: items.length + (hasMoreItems ? 1 : 1), // +1 for footer
        itemBuilder: (context, index) {
          if (index == items.length) {
            // Footer
            if (isLoadingMore) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              );
            } else if (!hasMoreItems) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(
                  child: Text(
                    '— einde —',
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              );
            } else {
              return const SizedBox.shrink();
            }
          }

          return NewsCard(item: items[index]);
        },
      ),
    );
  }
}

class NewsPage extends StatefulWidget {
  const NewsPage({super.key});

  @override
  State<NewsPage> createState() => _NewsPageState();
}

class _NewsPageState extends State<NewsPage> {
  List<NewsItem> items = [];
  bool isLoading = false;
  bool isLoadingMore = false;
  String? selectedLang;
  int limit = 20;
  int offset = 0;
  bool hasMoreItems = true;
  String? error;

  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadNews();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= 
        _scrollController.position.maxScrollExtent - 200) {
      _loadMoreNews();
    }
  }

  Future<void> _loadNews({bool refresh = false}) async {
    if (isLoading) return;

    setState(() {
      isLoading = true;
      error = null;
      if (refresh) {
        offset = 0;
        hasMoreItems = true;
      }
    });

    try {
      final response = await NewsService.fetchNews(
        lang: selectedLang,
        limit: limit,
        offset: offset,
      );

      setState(() {
        if (refresh) {
          items = response.items;
        } else {
          items.addAll(response.items);
        }
        hasMoreItems = response.items.length == limit;
        offset += response.items.length;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
        isLoading = false;
      });
    }
  }

  Future<void> _loadMoreNews() async {
    if (isLoadingMore || !hasMoreItems) return;

    setState(() {
      isLoadingMore = true;
    });

    try {
      final response = await NewsService.fetchNews(
        lang: selectedLang,
        limit: limit,
        offset: offset,
      );

      setState(() {
        items.addAll(response.items);
        hasMoreItems = response.items.length == limit;
        offset += response.items.length;
        isLoadingMore = false;
      });
    } catch (e) {
      setState(() {
        isLoadingMore = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load more: $e')),
        );
      }
    }
  }

  void _onLanguageChanged(String? lang) {
    setState(() {
      selectedLang = lang;
      offset = 0;
    });
    _loadNews(refresh: true);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Language Filter Chips
        Container(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Text('Language: ', style: TextStyle(fontWeight: FontWeight.w500)),
              const SizedBox(width: 8),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      FilterChip(
                        label: const Text('All'),
                        selected: selectedLang == null,
                        onSelected: (selected) => _onLanguageChanged(null),
                      ),
                      const SizedBox(width: 8),
                      FilterChip(
                        label: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('🇳🇱'),
                            SizedBox(width: 4),
                            Text('NL'),
                          ],
                        ),
                        selected: selectedLang == 'nl',
                        onSelected: (selected) => _onLanguageChanged(selected ? 'nl' : null),
                      ),
                      const SizedBox(width: 8),
                      FilterChip(
                        label: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('🇹🇷'),
                            SizedBox(width: 4),
                            Text('TR'),
                          ],
                        ),
                        selected: selectedLang == 'tr',
                        onSelected: (selected) => _onLanguageChanged(selected ? 'tr' : null),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        // News List
        Expanded(
          child: _buildContent(),
        ),
      ],
    );
  }

  Widget _buildContent() {
    if (isLoading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (error != null && items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text('Failed to load news', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _loadNews(refresh: true),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (items.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.article_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('No news items', style: TextStyle(fontSize: 18)),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _loadNews(refresh: true),
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(16),
        itemCount: items.length + 1, // +1 for footer
        itemBuilder: (context, index) {
          if (index == items.length) {
            // Footer
            if (isLoadingMore) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              );
            } else if (!hasMoreItems) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(
                  child: Text(
                    '— einde —',
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              );
            } else {
              return const SizedBox.shrink();
            }
          }

          return NewsCard(item: items[index]);
        },
      ),
    );
  }
}

class NewsCard extends StatefulWidget {
  final NewsItem item;

  const NewsCard({super.key, required this.item});

  @override
  State<NewsCard> createState() => _NewsCardState();
}

class _NewsCardState extends State<NewsCard> {
  Map<String, int> reactions = {};
  Set<String> userReactions = {};

  @override
  void initState() {
    super.initState();
    reactions = Map<String, int>.from(widget.item.reactions);
  }

  Future<void> toggleReaction(String emoji) async {
    try {
      final newReactions = await NewsService.toggleReaction(widget.item.id, emoji);
      setState(() {
        reactions = newReactions;
        if (userReactions.contains(emoji)) {
          userReactions.remove(emoji);
        } else {
          userReactions.add(emoji);
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to react: $e')),
        );
      }
    }
  }

  String _getLanguageChip(String lang) {
    final normalizedLang = lang.toLowerCase();
    if (normalizedLang.startsWith('nl')) return 'NL';
    if (normalizedLang.startsWith('tr')) return 'TR';
    return lang.toUpperCase();
  }

  Color _getLanguageColor(String lang) {
    final normalizedLang = lang.toLowerCase();
    if (normalizedLang.startsWith('nl')) return Colors.orange;
    if (normalizedLang.startsWith('tr')) return Colors.red;
    return Colors.grey;
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 2,
      child: InkWell(
        onTap: () async {
          if (widget.item.url.isNotEmpty && !widget.item.url.contains('example.com')) {
            final Uri uri = Uri.parse(widget.item.url);
            if (await canLaunchUrl(uri)) {
              await launchUrl(uri);
            }
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with source and language chip - TDA-15
              Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.item.sourceName,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  // Language Chip - TDA-15
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _getLanguageColor(widget.item.lang).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _getLanguageColor(widget.item.lang).withOpacity(0.3),
                      ),
                    ),
                    child: Text(
                      _getLanguageChip(widget.item.lang),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: _getLanguageColor(widget.item.lang),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Title - TDA-14
              Text(
                widget.item.title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 8),
              // Date - TDA-14
              Text(
                DateFormat('dd MMM yyyy, HH:mm').format(widget.item.publishedAt),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              // Summary - TDA-14
              if (widget.item.displaySummary.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  widget.item.displaySummary,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              // Tags and regions
              if (widget.item.tags.isNotEmpty || widget.item.regions.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    ...widget.item.regions.map((region) => Chip(
                          label: Text(
                            region,
                            style: const TextStyle(fontSize: 12),
                          ),
                          backgroundColor: Colors.blue.shade100,
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        )),
                    ...widget.item.tags.map((tag) => Chip(
                          label: Text(
                            tag,
                            style: const TextStyle(fontSize: 12),
                          ),
                          backgroundColor: Colors.green.shade100,
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        )),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              // Reactions and actions
              Row(
                children: [
                  _buildReactionButton('👍', reactions['👍'] ?? 0),
                  _buildReactionButton('❤️', reactions['❤️'] ?? 0),
                  _buildReactionButton('😂', reactions['😂'] ?? 0),
                  _buildReactionButton('🔥', reactions['🔥'] ?? 0),
                  const Spacer(),
                  if (!widget.item.url.contains('example.com'))
                    TextButton.icon(
                      icon: const Icon(Icons.open_in_new, size: 16),
                      label: const Text('Read More'),
                      onPressed: () async {
                        final Uri uri = Uri.parse(widget.item.url);
                        if (await canLaunchUrl(uri)) {
                          await launchUrl(uri);
                        }
                      },
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReactionButton(String emoji, int count) {
    final isSelected = userReactions.contains(emoji);
    
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: InkWell(
        onTap: () => toggleReaction(emoji),
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: isSelected ? Colors.blue.shade100 : Colors.grey.shade100,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: isSelected ? Colors.blue.shade300 : Colors.grey.shade300,
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(emoji, style: const TextStyle(fontSize: 16)),
              if (count > 0) ...[
                const SizedBox(width: 4),
                Text(
                  count.toString(),
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? Colors.blue.shade700 : Colors.grey.shade700,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}