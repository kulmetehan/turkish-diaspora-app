// Translation key types - ensures type safety for translation keys
export type TranslationKeys = {
  onboarding: {
    language: {
      title: string;
      subtitle: string;
      dutch: string;
      turkish: string;
    };
    welcome: {
      greeting: string;
      subtitle: string;
      continue: string;
    };
    explanation: {
      features: {
        news: string;
        newsSubtitle: string;
        locations: string;
        locationsSubtitle: string;
        events: string;
        eventsSubtitle: string;
      };
      cta: string;
    };
    homeCity: {
      title: string;
      subtitle: string;
      placeholder: string;
      searching: string;
      noResults: string;
      minChars: string;
      selected: string;
      previous: string;
      continue: string;
    };
    memleket: {
      title: string;
      subtitle: string;
      subtitleMultiple: string;
      placeholder: string;
      searching: string;
      noResults: string;
      minChars: string;
      multiple: string;
      skip: string;
      selected: string;
      selectedCount: string;
      selectedCountPlural: string;
      continue: string;
    };
    gender: {
      title: string;
      label: string;
      male: string;
      female: string;
      preferNotToSay: string;
    };
    success: {
      title: string;
      subtitle: string;
      badge: string;
      badgeTitle: string;
      cta: string;
    };
    username: {
      title: string;
      label: string;
      subtitle: string;
      placeholder: string;
      checking: string;
      available: string;
      taken: string;
      minChars: string;
      uploadPhoto: string;
      changePhoto: string;
      uploading: string;
      removeAvatar: string;
      complete: string;
      submitting: string;
    };
    complete: {
      success: string;
      error: string;
    };
  };
  account: {
    tabs: {
      general: string;
      privacy: string;
      notifications: string;
      history: string;
      about: string;
    };
    login: {
      notLoggedIn: string;
      description: string;
      or: string;
      emailPassword: string;
      logout: string;
      user: string;
    };
    profile: {
      title: string;
      description: string;
      username: string;
      noUsername: string;
      changePhoto: string;
      newPhotoSelected: string;
      save: string;
      saving: string;
      cancel: string;
      edit: string;
      uploading: string;
      daysRemaining: string;
      daysRemainingPlural: string;
    };
    display: {
      title: string;
      description: string;
      language: string;
      theme: string;
    };
    legal: {
      title: string;
      privacy: string;
      terms: string;
      guidelines: string;
    };
    history: {
      title: string;
    };
  };
  navigation: {
    feed: string;
    news: string;
    map: string;
    events: string;
  };
  common: {
    buttons: {
      save: string;
      cancel: string;
      delete: string;
      edit: string;
      search: string;
      filter: string;
      sort: string;
      close: string;
      back: string;
      next: string;
      previous: string;
      submit: string;
      loading: string;
    };
    loading: string;
    errors: {
      required: string;
      invalid: string;
      minLength: string;
      maxLength: string;
    };
    status: {
      verified: string;
      candidate: string;
      rejected: string;
      unknown: string;
    };
  };
  feed: {
    greeting: {
      morning: string;
      afternoon: string;
      evening: string;
      subtitle: string;
    };
    filters: {
      all: string;
      timeline: string;
      polls: string;
      checkIns: string;
      notes: string;
      oneCikanlar: string;
    };
    toast: {
      reactionError: string;
      bookmarkAddError: string;
    };
    card: {
      anonymousUser: string;
      promoted: string;
      deleteAsAdmin: string;
      activity: {
        checkIn: string;
        reaction: string;
        note: string;
        pollResponse: string;
        favorite: string;
        event: string;
        default: string;
      };
      time: {
        justNow: string;
        minutesAgo: string;
        hoursAgo: string;
      };
    };
    list: {
      emptyMessage: string;
      loadingMore: string;
      loadMore: string;
      loginToSeeActivity: string;
    };
    dashboard: {
      latestNews: string;
      viewAllNews: string;
      nearby: string;
      viewOnMap: string;
      events: string;
      viewAllEvents: string;
      activity: string;
      trendingNetherlands: string;
      trendingTurkey: string;
      viewAllTrends: string;
      noTrendsAvailable: string;
      notAvailable: string;
      newsLoading: string;
      noNewsAvailable: string;
      noEventsAvailable: string;
      activityItems: {
        checkInsToday: string;
        reactionsThisWeek: string;
        notesThisWeek: string;
        pollsThisWeek: string;
        favoritesThisWeek: string;
      };
    };
  };
  filters: {
    map: string;
    list: string;
    searchPlaceholder: string;
    searchAriaLabel: string;
    allCategories: string;
    categoryAriaLabel: string;
  };
  auth: {
    loginPrompt: {
      title: string;
      subtitle: string;
      emailPassword: string;
    };
    page: {
      title: string;
      subtitle: string;
      accountTitle: string;
      accountDescription: string;
      orEmailPassword: string;
      login: string;
      signup: string;
      email: string;
      password: string;
      displayName: string;
      displayNamePlaceholder: string;
      loginButton: string;
      loginButtonLoading: string;
      signupButton: string;
      signupButtonLoading: string;
      terms: string;
      termsLink: string;
      and: string;
      privacyLink: string;
    };
    toast: {
      welcomeBack: string;
      activityMigrated: string;
      loggedInGoogle: string;
      loggedIn: string;
      accountCreated: string;
      accountLinked: string;
      accountLinkedDescription: string;
      welcomeTurkspot: string;
      accountCreatedDescription: string;
      loginFailed: string;
      signupFailed: string;
      oauthFailed: string;
      unknownError: string;
    };
  };
  location: {
    category: string;
    aiConfidence: string;
    address: string;
    city: string;
    verificationState: string;
    claimLocation: string;
    closeDetails: string;
    noNotes: string;
    addNote: string;
    editNote: string;
    edited: string;
    deleting: string;
    verifiedByOwner: string;
    list: {
      noResults: string;
      warmingUp: string;
      loadError: string;
      noSearchResults: string;
      noLocationsInCity: string;
    };
    detail: {
      backToMap: string;
      backToList: string;
      removedFromFavorites: string;
      addedToFavorites: string;
      alreadyFavorite: string;
      favoriteError: string;
    };
  };
  map: {
    toggle: {
      map: string;
      list: string;
      mapView: string;
      listView: string;
    };
    checkIns: {
      showLocations: string;
      showCheckIns: string;
    };
    locationList: string;
    showOnMap: string;
    locationListAria: string;
  };
  news: {
    heading: string;
    promoted: string;
    feeds: {
      nl: string;
      tr: string;
      local: string;
      origin: string;
      trending: string;
      bookmarks: string;
    };
    categories: {
      turks_nieuws: string;
      general: string;
      sport: string;
      economie: string;
      cultuur: string;
      magazin: string;
    };
  };
  events: {
    heading: string;
    datePicker: {
      from: string;
      to: string;
      clear: string;
    };
    months: {
      jan: string;
      feb: string;
      mar: string;
      apr: string;
      may: string;
      jun: string;
      jul: string;
      aug: string;
      sep: string;
      oct: string;
      nov: string;
      dec: string;
    };
    categories: {
      club: string;
      theater: string;
      concert: string;
      familie: string;
    };
    formatters: {
      dateUnknown: string;
      unknown: string;
    };
    card: {
      reactionUpdateError: string;
    };
    viewMode: {
      list: string;
      map: string;
    };
  };
  toast: {
    logout: {
      success: string;
      error: string;
    };
    upload: {
      success: string;
      error: string;
      imageOnly: string;
      maxSize: string;
      previewFailed: string;
    };
    profile: {
      updated: string;
      updateFailed: string;
      usernameUpdated: string;
      usernameUpdateFailed: string;
      avatarUpdated: string;
      avatarUpdateFailed: string;
    };
    onboarding: {
      complete: string;
      completeError: string;
    };
    username: {
      minLength: string;
      maxLength: string;
      taken: string;
      checking: string;
    };
    poll: {
      voteSaved: string;
      voteError: string;
      pollDeleted: string;
      pollDeleteError: string;
      pollLoadError: string;
      pollsLoadError: string;
      contribution: string;
    };
    note: {
      updated: string;
      added: string;
    };
  };
  timeline: {
    filters: {
      all: string;
      polls: string;
      checkIns: string;
      notes: string;
    };
  };
  prikbord: {
    filters: {
      type: string;
      all: string;
      links: string;
      media: string;
      platform: string;
    };
    share: {
      shareLink: string;
      title: string;
      description: string;
      tabs: {
        link: string;
        media: string;
      };
      urlLabel: string;
      editPreview: string;
      editPreviewBad: string;
      manualPreview: string;
      titleLabel: string;
      descriptionLabel: string;
      imageUrlLabel: string;
      mediaLabel: string;
      dragDrop: string;
      mediaSize: string;
      previewCount: string;
      submit: string;
      submitting: string;
      uploading: string;
      errors: {
        urlRequired: string;
        invalidUrl: string;
        titleOrDescriptionRequired: string;
        mediaRequired: string;
      };
      success: {
        linkShared: string;
        mediaShared: string;
      };
    };
  };
  polls: {
    vote: string;
    saving: string;
    totalVotes: string;
    totalVotesPlural: string;
    loadingResults: string;
    sponsored: string;
    endsAt: string;
    deleteAsAdmin: string;
    confirmDelete: string;
  };
  report: {
    button: string;
    buttonAria: string;
    title: string;
    reporting: string;
    description: string;
    reason: string;
    selectReason: string;
    details: string;
    detailsPlaceholder: string;
    characterCount: string;
    submit: string;
    submitting: string;
    reasons: {
      noTurkishAffinity: string;
      permanentlyClosed: string;
      fakeSpam: string;
      other: string;
      spam: string;
      inappropriateContent: string;
      harassment: string;
      falseInformation: string;
      inappropriate: string;
      impersonation: string;
      inappropriateBehavior: string;
    };
    types: {
      location: string;
      note: string;
      reaction: string;
      user: string;
      checkIn: string;
      prikbordPost: string;
      poll: string;
    };
    errors: {
      reasonRequired: string;
      alreadyReported: string;
      submitFailed: string;
    };
    success: string;
  };
  categories: {
    restaurant: string;
    bakery: string;
    supermarket: string;
    barber: string;
    mosque: string;
    travelAgency: string;
    butcher: string;
    fastFood: string;
    cafe: string;
    automotive: string;
    insurance: string;
    tailor: string;
    eventsVenue: string;
    communityCentre: string;
    clinic: string;
    locationCount: string;
  };
};

// Helper type to extract nested keys as dot-notation strings
type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & (string | number)]: ObjectType[Key] extends object
    ? `${Key}` | `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : `${Key}`;
}[keyof ObjectType & (string | number)];

export type TranslationKey = NestedKeyOf<TranslationKeys>;

